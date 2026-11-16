import json
from importlib.resources import files
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from phreqed_dmx.tuning_profiles import (
    BUILTIN_TUNING_PROFILES,
    TuningProfileLibrary,
    parse_tuning_profile,
)


class TuningProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'tuning-profiles.json'

    def profile(self) -> dict:
        return dict(
            profile_id='user-tune-club',
            name='Club',
            description='Saved room response.',
            master_level=0.42,
            contrast=1.4,
            audio_auto_level=True,
            deep_dim_enabled=False,
            quiet_floor=0.03,
            white_preview_enabled=True,
            white_threshold=0.7,
            white_preview_level=0.75,
            white_output_level=0.05,
            white_drive_mode='effect',
            show_on_perform=False,
        )

    def test_builtin_stage_scales_are_safe_and_ordered(self) -> None:
        baseline = json.loads(
            files('phreqed_dmx').joinpath(
                'tuning_profiles.defaults.json'
            ).read_text(encoding='utf-8')
        )
        self.assertEqual(
            [profile['profile_id'] for profile in baseline['profiles']],
            ['rehearsal', 'small-stage', 'large-stage'],
        )
        rehearsal = BUILTIN_TUNING_PROFILES['rehearsal']
        small = BUILTIN_TUNING_PROFILES['small-stage']
        large = BUILTIN_TUNING_PROFILES['large-stage']
        self.assertEqual(rehearsal.master_level, 0.25)
        self.assertAlmostEqual(small.master_level, large.master_level * 0.75, 2)
        self.assertEqual(large.master_level, 0.65)
        self.assertTrue(small.white_preview_enabled)
        self.assertTrue(small.show_on_perform)
        self.assertLessEqual(large.white_output_level, 0.10)

    def test_legacy_profile_without_preview_flag_remains_compatible(self) -> None:
        legacy = self.profile()
        del legacy['white_preview_enabled']
        parsed = parse_tuning_profile(legacy)
        self.assertFalse(parsed.white_preview_enabled)

    def test_legacy_profile_without_perform_shortcut_remains_compatible(self) -> None:
        legacy = self.profile()
        del legacy['show_on_perform']
        parsed = parse_tuning_profile(legacy)
        self.assertFalse(parsed.show_on_perform)

    def test_legacy_profile_without_white_drive_uses_effect_mode(self) -> None:
        legacy = self.profile()
        del legacy['white_drive_mode']
        parsed = parse_tuning_profile(legacy)
        self.assertEqual(parsed.white_drive_mode, 'effect')

    def test_at_most_two_user_profiles_may_appear_on_perform(self) -> None:
        profiles = []
        for index in range(3):
            profile = self.profile()
            profile.update(
                profile_id=f'user-tune-club-{index}',
                name=f'Club {index}',
                show_on_perform=True,
            )
            profiles.append(profile)
        with self.assertRaisesRegex(ValueError, 'at most two'):
            TuningProfileLibrary(self.path).validate(
                dict(version=1, profiles=profiles)
            )

    def test_user_profiles_allow_full_white_range_but_reject_invalid_values(self) -> None:
        full = self.profile()
        full['white_output_level'] = 1.0
        self.assertEqual(parse_tuning_profile(full).white_output_level, 1.0)
        for key, value, message in (
            ('master_level', 0.66, 'master level'),
            ('white_output_level', 1.01, 'white output level'),
            ('contrast', 3.1, 'contrast'),
            ('white_drive_mode', 'unrestricted', 'white drive mode'),
            ('white_drive_mode', [], 'white drive mode'),
        ):
            profile = self.profile()
            profile[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, message):
                parse_tuning_profile(profile)

    def test_library_round_trips_atomically_and_keeps_builtins_immutable(self) -> None:
        library = TuningProfileLibrary(self.path)
        document = dict(version=1, profiles=[self.profile()])
        library.save(document)
        restored = TuningProfileLibrary(self.path)
        self.assertEqual(restored.document(), document)
        self.assertNotIn('rehearsal', restored.document()['profiles'])
        self.assertIn('rehearsal', restored.all_profiles)
        self.assertIn('user-tune-club', restored.all_profiles)

        before = self.path.read_bytes()
        with patch('phreqed_dmx.tuning_profiles.os.replace', side_effect=OSError):
            changed = json.loads(json.dumps(document))
            changed['profiles'][0]['name'] = 'Broken write'
            with self.assertRaises(OSError):
                restored.save(changed)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
