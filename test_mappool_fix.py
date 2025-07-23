#!/usr/bin/env python3
"""
Test script to validate the mappool upload logic fixes
"""
import re

def test_beatmap_id_extraction():
    """Test beatmap ID extraction from URLs"""
    test_urls = [
        "https://osu.ppy.sh/beatmapsets/1234567#osu/2345678",
        "https://osu.ppy.sh/b/2345678",
        "https://osu.ppy.sh/beatmaps/2345678",
        "osu.ppy.sh/beatmapsets/1234567#osu/2345678",
    ]
    
    for url in test_urls:
        m = re.search(r'#osu/(\d+)', url) or re.search(r'/(\d+)(?:$|\D)', url)
        if m:
            beatmap_id = int(m.group(1))
            print(f"URL: {url} -> ID: {beatmap_id}")
        else:
            print(f"URL: {url} -> FAILED to extract ID")

def test_map_links_parsing():
    """Test parsing multiple map links"""
    map_links = """
https://osu.ppy.sh/beatmapsets/1234567#osu/2345678
https://osu.ppy.sh/beatmapsets/1234568#osu/2345679
https://osu.ppy.sh/beatmapsets/1234569#osu/2345680
https://osu.ppy.sh/beatmapsets/1234570#osu/2345681
https://osu.ppy.sh/beatmapsets/1234571#osu/2345682
https://osu.ppy.sh/beatmapsets/1234572#osu/2345683
https://osu.ppy.sh/beatmapsets/1234573#osu/2345684
https://osu.ppy.sh/beatmapsets/1234574#osu/2345685
https://osu.ppy.sh/beatmapsets/1234575#osu/2345686
https://osu.ppy.sh/beatmapsets/1234576#osu/2345687
"""
    
    beatmap_ids = []
    for line in map_links.splitlines():
        url = line.strip()
        if not url:
            continue
        m = re.search(r'#osu/(\d+)', url) or re.search(r'/(\d+)(?:$|\D)', url)
        if m:
            beatmap_ids.append(int(m.group(1)))
    
    print(f"Extracted {len(beatmap_ids)} beatmap IDs: {beatmap_ids}")
    return len(beatmap_ids) == 10

if __name__ == "__main__":
    print("Testing beatmap ID extraction...")
    test_beatmap_id_extraction()
    print("\nTesting map links parsing...")
    success = test_map_links_parsing()
    print(f"Map links parsing test: {'PASSED' if success else 'FAILED'}")
