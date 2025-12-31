import requests
import math
from pyperclip import copy

# Chapter structure: chapter number -> total verses
CHAPTERS_STRUCTURE = {
    '1': 7, '2': 286, '3': 200, '4': 176, '5': 120, '6': 165, '7': 206, '8': 75,
    '9': 129, '10': 109, '11': 123, '12': 111, '13': 43, '14': 52, '15': 99,
    '16': 128, '17': 111, '18': 110, '19': 98, '20': 135, '21': 112, '22': 78,
    '23': 118, '24': 64, '25': 77, '26': 227, '27': 93, '28': 88, '29': 69,
    '30': 60, '31': 34, '32': 30, '33': 73, '34': 54, '35': 45, '36': 83,
    '37': 182, '38': 88, '39': 75, '40': 85, '41': 54, '42': 53, '43': 89,
    '44': 59, '45': 37, '46': 35, '47': 38, '48': 29, '49': 18, '50': 45,
    '51': 60, '52': 49, '53': 62, '54': 55, '55': 78, '56': 96, '57': 29,
    '58': 22, '59': 24, '60': 13, '61': 14, '62': 11, '63': 11, '64': 18,
    '65': 12, '66': 12, '67': 30, '68': 52, '69': 52, '70': 44, '71': 28,
    '72': 28, '73': 20, '74': 56, '75': 40, '76': 31, '77': 50, '78': 40,
    '79': 46, '80': 42, '81': 29, '82': 19, '83': 36, '84': 25, '85': 22,
    '86': 17, '87': 19, '88': 26, '89': 30, '90': 20, '91': 15, '92': 21,
    '93': 11, '94': 8, '95': 8, '96': 19, '97': 5, '98': 8, '99': 8,
    '100': 11, '101': 11, '102': 8, '103': 3, '104': 9, '105': 5, '106': 4,
    '107': 7, '108': 3, '109': 6, '110': 3, '111': 5, '112': 4, '113': 5, '114': 6
}

# Translation IDs for different languages
TRANSLATION_IDS = {
    'en': '131',  # English
    'ur': '234',  # Urdu
}

# Word-by-word translation language codes
WORD_LANGUAGES = {
    'en': 'en',
    'ur': 'ur',
}


def find_smallest_per_page(start_item, end_item):
    """Find the smallest per_page value that covers the range in one page."""
    per_page = 1
    while True:
        page_number = math.ceil(start_item / per_page)
        start_index = (page_number - 1) * per_page + 1
        end_index = page_number * per_page
        if end_index >= end_item:
            return per_page, page_number
        per_page += 1


def calculate_verse_ranges(verse_start, verse_count):
    """
    Calculate which chapters and verses to fetch.
    Returns a list of tuples: (chapter, start_verse, end_verse)
    """
    chapter = int(verse_start.split(":")[0])
    start_verse = int(verse_start.split(":")[1])

    ranges = []
    remaining = verse_count

    while remaining > 0:
        total_in_chapter = CHAPTERS_STRUCTURE[str(chapter)]
        available = total_in_chapter - start_verse + 1
        take = min(remaining, available)

        ranges.append((chapter, start_verse, start_verse + take - 1))

        remaining -= take
        chapter += 1
        start_verse = 1

    return ranges


def fetch_verses(verse_start, verse_count, language='ur', word_language='ur'):
    """
    Fetch Quran verses with translations.

    Args:
        verse_start: Starting verse (e.g., "2:29")
        verse_count: Number of verses to fetch
        language: Translation language ('en' or 'ur')
        word_language: Word-by-word translation language ('en' or 'ur')

    Returns:
        List of verse dictionaries with verse_key, arabic_text, and translation
    """
    translation_id = TRANSLATION_IDS.get(language, '234')
    word_lang = WORD_LANGUAGES.get(word_language, 'ur')

    ranges = calculate_verse_ranges(verse_start, verse_count)
    all_verses = []

    headers = {
        'accept': '*/*',
        'referer': 'https://quran.com/',
    }

    for chapter, start_verse, end_verse in ranges:
        per_page, page_number = find_smallest_per_page(start_verse, end_verse)

        params = {
            'words': 'true',
            'translations': translation_id,
            'word_translation_language': word_lang,
            'word_fields': 'verse_key,position,text_uthmani,char_type_name',
            'page': str(page_number),
            'per_page': str(per_page),
        }

        url = f'https://quran.com/api/proxy/content/api/qdc/verses/by_chapter/{chapter}'

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for verse in data.get('verses', []):
                verse_key = verse.get('verse_key', '')
                v_chapter, v_num = verse_key.split(':')
                v_num = int(v_num)

                # Only include verses in our range
                if start_verse <= v_num <= end_verse:
                    # Get Arabic text
                    arabic_text = verse.get('text_uthmani', '')

                    # Get translation
                    translations = verse.get('translations', [])
                    translation_text = translations[0].get('text', '') if translations else ''

                    # Get word-by-word data
                    words = []
                    for word in verse.get('words', []):
                        if word.get('char_type_name') == 'word':
                            words.append({
                                'arabic': word.get('text_uthmani', ''),
                                'translation': word.get('translation', {}).get('text', '')
                            })

                    all_verses.append({
                        'verse_key': verse_key,
                        'verse_number': v_num,
                        'arabic_text': arabic_text,
                        'translation': translation_text,
                        'words': words
                    })

        except requests.RequestException as e:
            print(f"Error fetching chapter {chapter}: {e}")

    return all_verses


def format_verses(verses, show_words=False):
    """Format verses for display."""
    output = []

    for verse in verses:
        verse_num = verse['verse_key'].split(':')[1]
        translation = verse['translation']

        output.append(f"\t{verse_num}.\t{translation}")

        if show_words and verse['words']:
            word_line = " | ".join([f"{w['arabic']} ({w['translation']})" for w in verse['words']])
            output.append(f"\t  {word_line}")

    return "\n".join(output)


def main():
    # Example usage
    verse_start = "2:285"
    verse_count = 3
    language = "ur"  # Full translation language
    word_language = "ur"  # Word-by-word language

    print(f"Fetching {verse_count} verses starting from {verse_start}")
    print(f"Translation: {language}, Word-by-word: {word_language}")
    print("-" * 50)

    verses = fetch_verses(
        verse_start=verse_start,
        verse_count=verse_count,
        language=language,
        word_language=word_language
    )

    formatted = format_verses(verses, show_words=False)
    print(formatted)
    copy(formatted)

if __name__ == "__main__":
    main()