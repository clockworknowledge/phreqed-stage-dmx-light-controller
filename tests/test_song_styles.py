import unittest

from phreqed_dmx.presets import PRESETS
from phreqed_dmx.song_styles import STYLE_TEMPLATES, generate_style_cues
from phreqed_dmx.songs import SongStyle


class SongStyleTemplateTests(unittest.TestCase):
    def test_all_four_styles_are_deterministic_valid_and_distinct(self):
        rendered = {}
        for style in (SongStyle.PUNK, SongStyle.ROCK, SongStyle.MELLOW, SongStyle.FUNK):
            with self.subTest(style=style.value):
                first = generate_style_cues(style, 180.0, set(PRESETS))
                second = generate_style_cues(style, 180.0, set(PRESETS))
                self.assertEqual(first, second)
                self.assertEqual(first[0].at_seconds, 0.0)
                self.assertTrue(all(
                    left.at_seconds < right.at_seconds
                    for left, right in zip(first, first[1:])
                ))
                self.assertLess(first[-1].at_seconds, 180.0)
                self.assertTrue(all(cue.preset_id in PRESETS for cue in first))
                rendered[style] = tuple(cue.preset_id for cue in first)
        self.assertEqual(len(set(rendered.values())), 4)
        self.assertEqual(set(STYLE_TEMPLATES), {
            SongStyle.PUNK, SongStyle.ROCK, SongStyle.MELLOW, SongStyle.FUNK,
        })

    def test_short_song_still_has_strictly_increasing_cues(self):
        cues = generate_style_cues('punk', 1.0, set(PRESETS))
        self.assertTrue(all(
            left.at_seconds < right.at_seconds
            for left, right in zip(cues, cues[1:])
        ))

    def test_unspecified_unknown_and_missing_presets_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'choose punk'):
            generate_style_cues('unspecified', 120.0, set(PRESETS))
        with self.assertRaisesRegex(ValueError, 'style is invalid'):
            generate_style_cues('metal', 120.0, set(PRESETS))
        with self.assertRaisesRegex(ValueError, 'missing preset'):
            generate_style_cues('rock', 120.0, {'psychedelic-bloom'})


if __name__ == '__main__':
    unittest.main()
