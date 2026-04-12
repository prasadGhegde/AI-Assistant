import unittest

from morning_briefs.tts import chunk_for_tts
from morning_briefs.utils import normalize_story_key


class UtilsTest(unittest.TestCase):
    def test_story_key_ignores_common_words(self):
        self.assertEqual(
            normalize_story_key("The New AI Deal in the Market"),
            "ai deal market",
        )

    def test_tts_chunker_preserves_short_text(self):
        text = "Good morning. This is a briefing."
        self.assertEqual(chunk_for_tts(text), [text])


if __name__ == "__main__":
    unittest.main()
