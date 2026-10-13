"""Reference parsing: what people actually type, and what it must mean."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripture import refparse  # noqa: E402
from scripture.refparse import RefError, Segment  # noqa: E402

N = None
EN = chr(0x2013)  # an en dash, as a phone or a word processor types it
EM = chr(0x2014)

# (typed, book USFM, segments as (c1, v1, c2, v2), display)
CASES = [
    ("John 3:16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("jn 3 16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("Jn3:16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("jn3v16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("John 3 v 16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("John 3.16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("john 3:16-18", "JHN", [(3, 16, 3, 18)], "John 3:16-18"),
    ("John 3:16 - 18", "JHN", [(3, 16, 3, 18)], "John 3:16-18"),
    ("John 3:16" + EN + "18", "JHN", [(3, 16, 3, 18)], "John 3:16-18"),
    ("John 3:16" + EM + "18", "JHN", [(3, 16, 3, 18)], "John 3:16-18"),
    ("jn 3 16-18", "JHN", [(3, 16, 3, 18)], "John 3:16-18"),
    ("Jhon 3:16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("Joh 1:1", "JHN", [(1, 1, 1, 1)], "John 1:1"),
    ("1 Cor 13:4-7", "1CO", [(13, 4, 13, 7)], "1 Corinthians 13:4-7"),
    ("1cor 13:4-7", "1CO", [(13, 4, 13, 7)], "1 Corinthians 13:4-7"),
    ("I Corinthians 13", "1CO", [(13, N, 13, N)], "1 Corinthians 13"),
    ("First Corinthians 13:13", "1CO", [(13, 13, 13, 13)], "1 Corinthians 13:13"),
    ("1st Cor 13:13", "1CO", [(13, 13, 13, 13)], "1 Corinthians 13:13"),
    ("2 Cor 5:17", "2CO", [(5, 17, 5, 17)], "2 Corinthians 5:17"),
    ("II Cor 5:17", "2CO", [(5, 17, 5, 17)], "2 Corinthians 5:17"),
    ("Ps 23", "PSA", [(23, N, 23, N)], "Psalm 23"),
    ("Psalm 23", "PSA", [(23, N, 23, N)], "Psalm 23"),
    ("Psalms 23:1-3", "PSA", [(23, 1, 23, 3)], "Psalm 23:1-3"),
    ("psa 119:105", "PSA", [(119, 105, 119, 105)], "Psalm 119:105"),
    ("Ps 23-24", "PSA", [(23, N, 24, N)], "Psalms 23-24"),
    ("Gen 1:1-2:3", "GEN", [(1, 1, 2, 3)], "Genesis 1:1-2:3"),
    ("Genesis 1", "GEN", [(1, N, 1, N)], "Genesis 1"),
    ("Genisis 1:1", "GEN", [(1, 1, 1, 1)], "Genesis 1:1"),
    ("gn 1 1", "GEN", [(1, 1, 1, 1)], "Genesis 1:1"),
    ("Exodous 20", "EXO", [(20, N, 20, N)], "Exodus 20"),
    ("Ex 20:1-17", "EXO", [(20, 1, 20, 17)], "Exodus 20:1-17"),
    ("Deu 6:4", "DEU", [(6, 4, 6, 4)], "Deuteronomy 6:4"),
    ("Deut 6:4-9", "DEU", [(6, 4, 6, 9)], "Deuteronomy 6:4-9"),
    ("Josh 1:9", "JOS", [(1, 9, 1, 9)], "Joshua 1:9"),
    ("Judg 6:12", "JDG", [(6, 12, 6, 12)], "Judges 6:12"),
    ("Ruth 1:16", "RUT", [(1, 16, 1, 16)], "Ruth 1:16"),
    ("1 Sam 17:45", "1SA", [(17, 45, 17, 45)], "1 Samuel 17:45"),
    ("1 Kgs 19:12", "1KI", [(19, 12, 19, 12)], "1 Kings 19:12"),
    ("2 Chron 7:14", "2CH", [(7, 14, 7, 14)], "2 Chronicles 7:14"),
    ("Neh 8:10", "NEH", [(8, 10, 8, 10)], "Nehemiah 8:10"),
    ("Esth 4:14", "EST", [(4, 14, 4, 14)], "Esther 4:14"),
    ("Job 19:25", "JOB", [(19, 25, 19, 25)], "Job 19:25"),
    ("Prov 3:5-6", "PRO", [(3, 5, 3, 6)], "Proverbs 3:5-6"),
    ("Ecc 3:1-8", "ECC", [(3, 1, 3, 8)], "Ecclesiastes 3:1-8"),
    ("Song of Solomon 2:4", "SNG", [(2, 4, 2, 4)], "Song of Solomon 2:4"),
    ("Song of Songs 8:7", "SNG", [(8, 7, 8, 7)], "Song of Solomon 8:7"),
    ("is 53:5", "ISA", [(53, 5, 53, 5)], "Isaiah 53:5"),
    ("Isa 40:31", "ISA", [(40, 31, 40, 31)], "Isaiah 40:31"),
    ("Jer 29:11", "JER", [(29, 11, 29, 11)], "Jeremiah 29:11"),
    ("Lam 3:22-23", "LAM", [(3, 22, 3, 23)], "Lamentations 3:22-23"),
    ("Ezek 37:4", "EZK", [(37, 4, 37, 4)], "Ezekiel 37:4"),
    ("Dan 3:17", "DAN", [(3, 17, 3, 17)], "Daniel 3:17"),
    ("Joel 2:28", "JOL", [(2, 28, 2, 28)], "Joel 2:28"),
    ("Amos 5:24", "AMO", [(5, 24, 5, 24)], "Amos 5:24"),
    ("Jonah 2", "JON", [(2, N, 2, N)], "Jonah 2"),
    ("Mic 6:8", "MIC", [(6, 8, 6, 8)], "Micah 6:8"),
    ("Hab 3:17-18", "HAB", [(3, 17, 3, 18)], "Habakkuk 3:17-18"),
    ("Zeph 3:17", "ZEP", [(3, 17, 3, 17)], "Zephaniah 3:17"),
    ("Mal 3:10", "MAL", [(3, 10, 3, 10)], "Malachi 3:10"),
    ("Matt 5:3-12", "MAT", [(5, 3, 5, 12)], "Matthew 5:3-12"),
    ("Mathew 6:9-13", "MAT", [(6, 9, 6, 13)], "Matthew 6:9-13"),
    ("Mt 28:19", "MAT", [(28, 19, 28, 19)], "Matthew 28:19"),
    ("Mk 1:1,3,5-7", "MRK", [(1, 1, 1, 1), (1, 3, 1, 3), (1, 5, 1, 7)], "Mark 1:1, 3, 5-7"),
    ("Mark 16", "MRK", [(16, N, 16, N)], "Mark 16"),
    ("Lk 2:1-14", "LUK", [(2, 1, 2, 14)], "Luke 2:1-14"),
    ("Luke 15:11-32", "LUK", [(15, 11, 15, 32)], "Luke 15:11-32"),
    ("John 3:16-4:2; 5:1", "JHN", [(3, 16, 4, 2), (5, 1, 5, 1)], "John 3:16-4:2, 5:1"),
    ("John 11:35", "JHN", [(11, 35, 11, 35)], "John 11:35"),
    ("Acts 2:38", "ACT", [(2, 38, 2, 38)], "Acts 2:38"),
    ("Romans 8:28, 31-39", "ROM", [(8, 28, 8, 28), (8, 31, 8, 39)], "Romans 8:28, 31-39"),
    ("Rom 12:1-2", "ROM", [(12, 1, 12, 2)], "Romans 12:1-2"),
    ("Gal 5:22-23", "GAL", [(5, 22, 5, 23)], "Galatians 5:22-23"),
    ("Eph 2:8-9", "EPH", [(2, 8, 2, 9)], "Ephesians 2:8-9"),
    ("Phil 4:6-7", "PHP", [(4, 6, 4, 7)], "Philippians 4:6-7"),
    ("Phillipians 4:13", "PHP", [(4, 13, 4, 13)], "Philippians 4:13"),
    ("Col 3:23", "COL", [(3, 23, 3, 23)], "Colossians 3:23"),
    ("1 Thess 5:16-18", "1TH", [(5, 16, 5, 18)], "1 Thessalonians 5:16-18"),
    ("2 Tim 3:16-17", "2TI", [(3, 16, 3, 17)], "2 Timothy 3:16-17"),
    ("Titus 2:11", "TIT", [(2, 11, 2, 11)], "Titus 2:11"),
    ("Phlm 6", "PHM", [(1, 6, 1, 6)], "Philemon 1:6"),
    ("Philemon", "PHM", [(1, N, 1, N)], "Philemon 1"),
    ("Heb 11", "HEB", [(11, N, 11, N)], "Hebrews 11"),
    ("Heb 11:1", "HEB", [(11, 1, 11, 1)], "Hebrews 11:1"),
    ("Jas 1:2-4", "JAS", [(1, 2, 1, 4)], "James 1:2-4"),
    ("1 Pet 5:7", "1PE", [(5, 7, 5, 7)], "1 Peter 5:7"),
    ("1jn1:9", "1JN", [(1, 9, 1, 9)], "1 John 1:9"),
    ("first john 4:8", "1JN", [(4, 8, 4, 8)], "1 John 4:8"),
    ("3 John 2", "3JN", [(1, 2, 1, 2)], "3 John 1:2"),
    ("Jude 3", "JUD", [(1, 3, 1, 3)], "Jude 1:3"),
    ("Jude 24-25", "JUD", [(1, 24, 1, 25)], "Jude 1:24-25"),
    ("Obadiah", "OBA", [(1, N, 1, N)], "Obadiah 1"),
    ("Rev 21:4", "REV", [(21, 4, 21, 4)], "Revelation 21:4"),
    ("Revelations 21:4", "REV", [(21, 4, 21, 4)], "Revelation 21:4"),
    ("rev 22", "REV", [(22, N, 22, N)], "Revelation 22"),
    ("  john   3 :  16  ", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("JOHN 3:16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
    ("Jn. 3:16", "JHN", [(3, 16, 3, 16)], "John 3:16"),
]

ERRORS = [
    ("John 22", "21 chapters"),
    ("John 3:18-16", "backwards"),
    ("zzz 3:1", "no book called"),
    ("Corinthians 13", "1 Corinthians or 2 Corinthians"),
    ("", "type a reference"),
    ("John 3:0", "start at 1"),
    ("Jude 2:1", "1 chapter"),
]


class ReferenceTable(unittest.TestCase):
    def test_every_typed_reference(self):
        for typed, book, segments, display in CASES:
            with self.subTest(typed=typed):
                ref = refparse.parse(typed)
                self.assertEqual(ref.book.usfm, book)
                self.assertEqual([s.as_tuple() for s in ref.segments], segments)
                self.assertEqual(ref.display(), display)

    def test_refusals_say_what_to_do(self):
        for typed, words in ERRORS:
            with self.subTest(typed=typed):
                with self.assertRaises(RefError) as caught:
                    refparse.parse(typed)
                self.assertIn(words, str(caught.exception))

    def test_a_translation_on_the_end(self):
        ref = refparse.parse("John 3:16 KJV", ["kjv", "web"])
        self.assertEqual(ref.translation, "kjv")
        ref = refparse.parse("Ps 23 (web)", ["kjv", "web"])
        self.assertEqual(ref.translation, "web")
        self.assertEqual(ref.display(), "Psalm 23")

    def test_words_are_a_search_not_a_reference(self):
        self.assertIsNone(refparse.try_parse("love one another"))
        self.assertIsNone(refparse.try_parse("acts of the apostles"))
        self.assertIsNotNone(refparse.try_parse("am 5 24"))

    def test_every_book_reads_by_its_own_name_and_codes(self):
        from scripture import books
        for book in books.ALL:
            for name in [book.name, book.usfm, book.osis] + book.aliases:
                with self.subTest(name=name):
                    self.assertIs(refparse.parse("%s 1:1" % name).book, book)

    def test_segment_equality(self):
        self.assertEqual(Segment(1, 2, 1, 3), Segment(1, 2, 1, 3))


if __name__ == "__main__":
    unittest.main()
