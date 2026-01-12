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

# Translation IDs
TRANSLATION_IDS = {
    'en': '131',  # English - Saheeh International
    'ur': '234',  # Urdu - Fateh Muhammad Jalandhry
}

HEADERS = {
    'accept': '*/*',
    'referer': 'https://quran.com/',
}


def calculate_end_verse(verse_start, verse_count):
    """Calculate the ending verse key given a start and count."""
    chapter = int(verse_start.split(":")[0])
    start_verse = int(verse_start.split(":")[1])

    remaining = verse_count
    current_chapter = chapter
    current_verse = start_verse

    while remaining > 1:
        total_in_chapter = CHAPTERS_STRUCTURE[str(current_chapter)]
        available = total_in_chapter - current_verse + 1

        if remaining <= available:
            current_verse = current_verse + remaining - 1
            break
        else:
            remaining -= available
            current_chapter += 1
            current_verse = 1

    return f"{current_chapter}:{current_verse}"


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
    Calculate which chapters and verses to fetch for word-by-word.
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


def fetch_translations_advanced(verse_start, verse_end, languages=['en', 'ur']):
    """
    Fetch translations using the advanced_copy endpoint.
    Returns a dict mapping verse_key -> {lang: translation_text}
    """
    url = "https://quran.com/api/proxy/content/api/qdc/verses/advanced_copy"
    translations_map = {}

    for lang in languages:
        trans_id = TRANSLATION_IDS.get(lang, '131')
        params = {
            "raw": "true",
            "from": verse_start,
            "to": verse_end,
            "footnote": "false",
            "translator_name": "false",
            "translations": trans_id
        }

        try:
            response = requests.get(url, params=params, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            # Parse the result - it comes as a single text with verses
            result_text = data.get('result', '')

            # Split by verse markers - format is typically "(chapter:verse) text"
            # or just numbered verses
            lines = result_text.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Try to parse verse reference - look for patterns like (2:29) or 2:29
                import re
                match = re.match(r'\((\d+:\d+)\)\s*(.*)', line)
                if match:
                    verse_key = match.group(1)
                    text = match.group(2).strip()
                else:
                    # Try without parentheses
                    match = re.match(r'(\d+:\d+)\s*(.*)', line)
                    if match:
                        verse_key = match.group(1)
                        text = match.group(2).strip()
                    else:
                        continue

                if verse_key not in translations_map:
                    translations_map[verse_key] = {}
                translations_map[verse_key][lang] = text

        except requests.RequestException as e:
            print(f"Error fetching {lang} translations: {e}")

    return translations_map


def fetch_word_by_word(verse_start, verse_count, word_lang='en'):
    """
    Fetch word-by-word translations for a specific language.
    Returns a dict mapping verse_key -> list of word dicts
    """
    ranges = calculate_verse_ranges(verse_start, verse_count)
    words_map = {}

    for chapter, start_verse, end_verse in ranges:
        per_page, page_number = find_smallest_per_page(start_verse, end_verse)

        params = {
            'words': 'true',
            'word_translation_language': word_lang,
            'word_fields': 'verse_key,position,text_uthmani,char_type_name',
            'page': str(page_number),
            'per_page': str(per_page),
        }

        url = f'https://quran.com/api/proxy/content/api/qdc/verses/by_chapter/{chapter}'

        try:
            response = requests.get(url, headers=HEADERS, params=params)
            response.raise_for_status()
            data = response.json()

            for verse in data.get('verses', []):
                verse_key = verse.get('verse_key', '')
                v_chapter, v_num = verse_key.split(':')
                v_num = int(v_num)

                if start_verse <= v_num <= end_verse:
                    words = []
                    for word in verse.get('words', []):
                        if word.get('char_type_name') == 'word':
                            words.append({
                                'arabic': word.get('text_uthmani', ''),
                                'translation': word.get('translation', {}).get('text', '')
                            })
                    words_map[verse_key] = words

        except requests.RequestException as e:
            print(f"Error fetching word-by-word for chapter {chapter}: {e}")

    return words_map


def fetch_verses(verse_start, verse_count, languages=['en', 'ur'], word_languages=['en', 'ur']):
    """
    Fetch Quran verses with translations and word-by-word in multiple languages.

    Args:
        verse_start: Starting verse (e.g., "2:29")
        verse_count: Number of verses to fetch
        languages: List of translation languages (e.g., ['en', 'ur'])
        word_languages: List of word-by-word languages (e.g., ['en', 'ur'])

    Returns:
        List of verse dictionaries
    """
    verse_end = calculate_end_verse(verse_start, verse_count)

    # Fetch translations using advanced_copy
    translations_map = fetch_translations_advanced(verse_start, verse_end, languages)

    # Fetch word-by-word for each language
    word_maps = {}
    for word_lang in word_languages:
        word_maps[word_lang] = fetch_word_by_word(verse_start, verse_count, word_lang)

    # Build the verses list
    all_verses = []
    ranges = calculate_verse_ranges(verse_start, verse_count)

    for chapter, start_v, end_v in ranges:
        for v_num in range(start_v, end_v + 1):
            verse_key = f"{chapter}:{v_num}"

            # Combine word-by-word from different languages
            words = []
            # Use English words as base (for Arabic text)
            en_words = word_maps.get('en', {}).get(verse_key, [])
            ur_words = word_maps.get('ur', {}).get(verse_key, [])

            for i, en_word in enumerate(en_words):
                word_data = {
                    'arabic': en_word.get('arabic', ''),
                    'en': en_word.get('translation', ''),
                }
                # Add Urdu translation if available
                if i < len(ur_words):
                    word_data['ur'] = ur_words[i].get('translation', '')
                else:
                    word_data['ur'] = ''
                words.append(word_data)

            # Get Arabic text from words
            arabic_text = ' '.join([w['arabic'] for w in words])

            all_verses.append({
                'verse_key': verse_key,
                'verse_number': v_num,
                'arabic_text': arabic_text,
                'translations': translations_map.get(verse_key, {}),
                'words': words
            })

    return all_verses


def format_verses(verses, show_words=True):
    """Format verses for display with translations grouped by language."""
    output = []

    # Urdu section first
    output.append("Urdu Translation:")
    for verse in verses:
        verse_key = verse['verse_key']
        translations = verse['translations']
        if 'ur' in translations:
            output.append(f"\t{verse_key}.\t{translations['ur']}")

    output.append("")  # Blank line between sections

    # English section
    output.append("English Translation:")
    for verse in verses:
        verse_key = verse['verse_key']
        translations = verse['translations']
        if 'en' in translations:
            output.append(f"\t{verse_key}.\t{translations['en']}")

    if show_words:
        output.append("")
        output.append("Word-by-Word:")
        for verse in verses:
            verse_key = verse['verse_key']
            if verse['words']:
                output.append(f"\t{verse_key}.")
                for w in verse['words']:
                    en_trans = w.get('en', '')
                    ur_trans = w.get('ur', '')
                    arabic = w.get('arabic', '')
                    output.append(f"\t\t{en_trans} = {ur_trans} = {arabic}")
                output.append("")  # Blank line between verses

    return "\n".join(output)


def main():
    while True:
        verse_start = input("Enter starting verse (e.g., 2:29): ").strip()
        verse_count = int(input("Enter number of verses to fetch: ").strip())

        print(f"\nFetching {verse_count} verses starting from {verse_start}")
        print("Translations: English & Urdu")
        print("Word-by-Word: English & Urdu")
        print("-" * 50)

        verses = fetch_verses(
            verse_start=verse_start,
            verse_count=verse_count,
            languages=['en', 'ur'],
            word_languages=['en', 'ur']
        )

        formatted = format_verses(verses, show_words=True)
        print(formatted)
        copy(formatted)
        print("-" * 50)
        print("Copied to clipboard!")


if __name__ == "__main__":
    main()