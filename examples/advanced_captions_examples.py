"""
Advanced Captions Examples for YouTube Toolkit

Migrated to the 2.0.0 sub-API surface. Caption *listing* now goes through
``toolkit.get.captions(url)``, which returns a ``CaptionResult`` dataclass with:
  - ``.tracks``           -> list of ``CaptionTrack`` objects (attribute access)
  - ``.available_tracks`` -> only accessible tracks
  - ``.quota_cost``       -> int

Each ``CaptionTrack`` exposes ``.display_name``, ``.language``,
``.language_code``, ``.track_type``, ``.status``, ``.is_auto_generated``,
``.is_cc``, ``.is_manual``, ``.is_accessible``.

NOTE: Several caption helpers were removed in 2.0 with no sub-API equivalent:
``advanced_download_captions``, ``get_caption_analytics``, ``search_captions``,
``export_captions``, ``get_best_caption_track``, ``get_captions_in_format``.
The pure utility classes ``CaptionFormatConverter`` and ``CaptionAnalyzer`` are
still importable and are demonstrated below on caption text you already have.

To download captions to disk in 2.0, use ``toolkit.download.captions(url,
lang='en', format='srt')`` which returns the output file path.
"""

import os
from youtube_toolkit import YouTubeToolkit, CaptionFormatConverter, CaptionAnalyzer


def setup_toolkit():
    """Initialize YouTube Toolkit with verbose output."""
    return YouTubeToolkit(verbose=True)


def example_caption_listing():
    """Example 1: Caption Listing."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Caption Listing")
    print("="*70)

    toolkit = setup_toolkit()

    # List all available captions -> get.captions returns CaptionResult
    print("📋 Listing all available captions...")
    caption_result = toolkit.get.captions("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    print(f"Total tracks: {len(caption_result.tracks)}")
    print(f"Available tracks: {len(caption_result.available_tracks)}")
    print(f"Quota cost: {caption_result.quota_cost} units")

    # Display caption tracks (CaptionTrack objects -> attribute access)
    for i, track in enumerate(caption_result.tracks[:5], 1):
        print(f"\n{i}. {track.display_name}")
        print(f"   Language: {track.language_code}")
        print(f"   Type: {track.track_type}")
        print(f"   Status: {track.status}")
        print(f"   Auto-generated: {track.is_auto_generated}")
        print(f"   CC: {track.is_cc}")

    # NOTE: CaptionFilters(manual_only=...)/language filtering passed to
    # list_captions was removed from the sub-API. Filter client-side instead.
    print(f"\n🔍 Manual captions only (client-side filter)...")
    manual_tracks = [t for t in caption_result.tracks if t.is_manual]
    print(f"Manual tracks: {len(manual_tracks)}")

    print(f"\n🌍 English/Spanish tracks (client-side filter)...")
    lang_tracks = [t for t in caption_result.tracks if t.language_code in ('en', 'es')]
    print(f"English/Spanish tracks: {len(lang_tracks)}")


def example_caption_download():
    """Example 2: Caption Download."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Caption Download")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: `advanced_download_captions` (with rich analysis payload) was removed
    # in 2.0. Use download.captions(url, lang=, format=) which returns the
    # output file path.
    formats = ['srt', 'vtt', 'txt']

    for format_type in formats:
        print(f"\n📥 Downloading captions in {format_type.upper()} format...")
        try:
            output_path = toolkit.download.captions(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                lang='en',
                format=format_type,
            )
            print(f"✅ Downloaded: {output_path}")
        except Exception as e:
            print(f"❌ Error downloading {format_type}: {e}")


def example_caption_analysis():
    """Example 3: Caption Analysis from downloaded text."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Caption Analysis and Insights")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: `get_caption_analytics` was removed in 2.0. Download captions, then
    # use CaptionFormatConverter + CaptionAnalyzer to derive insights locally.
    print("📥 Downloading SRT captions for analysis...")
    try:
        srt_path = toolkit.download.captions(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            lang='en',
            format='srt',
        )

        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()

        cues = CaptionFormatConverter.parse_srt(srt_content)
        print(f"\n📊 Caption analysis ({len(cues)} cues):")

        # Reading-speed insights via CaptionAnalyzer
        reading_speed = CaptionAnalyzer.analyze_reading_speed(cues)
        print(f"   Average WPM: {reading_speed.get('average_wpm', 0):.1f}")
        print(f"   Total words: {reading_speed.get('total_words', 0)}")
        print(f"   Total duration: {reading_speed.get('total_duration', 0):.1f}s")

        # Gap analysis
        gaps = CaptionAnalyzer.find_gaps(cues)
        print(f"\n⏱️  Timing Gaps: {len(gaps)}")
        if gaps:
            avg_gap = sum(gap['duration'] for gap in gaps) / len(gaps)
            print(f"   Average gap: {avg_gap:.1f} seconds")
            print(f"   Longest gap: {max(gap['duration'] for gap in gaps):.1f} seconds")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")


def example_caption_search():
    """Example 4: Caption Content Search (client-side)."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Caption Content Search")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: `search_captions` was removed in 2.0. Download the captions and
    # search the parsed cues client-side.
    print("📥 Downloading captions to search...")
    try:
        srt_path = toolkit.download.captions(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            lang='en',
            format='srt',
        )
        with open(srt_path, 'r', encoding='utf-8') as f:
            cues = CaptionFormatConverter.parse_srt(f.read())
    except Exception as e:
        print(f"❌ Could not load captions: {e}")
        return

    search_terms = ["never", "gonna", "give", "up"]
    for term in search_terms:
        print(f"\n🔍 Searching for '{term}' in captions...")
        matches = [c for c in cues if term.lower() in c.text.lower()]
        print(f"Found {len(matches)} matches:")
        for i, cue in enumerate(matches[:3], 1):
            print(f"  {i}. [{cue.formatted_start} - {cue.formatted_end}]")
            print(f"     {cue.text}")
        if len(matches) > 3:
            print(f"     ... and {len(matches) - 3} more matches")


def example_caption_format_conversion():
    """Example 5: Caption Format Conversion."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Caption Format Conversion")
    print("="*70)

    toolkit = setup_toolkit()

    # Download SRT format, then convert with CaptionFormatConverter
    print("📥 Downloading SRT captions...")
    try:
        srt_path = toolkit.download.captions(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            lang='en',
            format='srt',
        )
        print(f"✅ SRT downloaded: {srt_path}")

        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()

        print(f"\n🔄 Converting formats...")

        # Convert to VTT
        vtt_content = CaptionFormatConverter.srt_to_vtt(srt_content)
        print(f"✅ Converted to WebVTT format ({len(vtt_content)} characters)")

        # Convert to plain text
        txt_content = CaptionFormatConverter.srt_to_txt(srt_content)
        print(f"✅ Converted to plain text ({len(txt_content)} characters)")

        # Parse SRT into cues
        cues = CaptionFormatConverter.parse_srt(srt_content)
        print(f"✅ Parsed into {len(cues)} caption cues")

        # Show sample cues
        print(f"\n📝 Sample caption cues:")
        for i, cue in enumerate(cues[:3], 1):
            print(f"  {i}. [{cue.formatted_start} - {cue.formatted_end}]")
            print(f"     {cue.text}")
            print(f"     Duration: {cue.duration:.1f}s")

    except Exception as e:
        print(f"❌ Format conversion failed: {e}")


def example_caption_export():
    """Example 6: Caption Export (via download in different formats)."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Caption Export")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: `export_captions` (json/csv) was removed in 2.0. Use
    # download.captions to write supported subtitle formats to disk.
    export_formats = ['srt', 'vtt', 'txt']

    for format_type in export_formats:
        print(f"\n📤 Exporting captions as {format_type.upper()}...")
        try:
            export_path = toolkit.download.captions(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                lang='en',
                format=format_type,
            )
            print(f"✅ Exported to: {export_path}")
            file_size = os.path.getsize(export_path)
            print(f"   File size: {file_size} bytes")
        except Exception as e:
            print(f"❌ Export failed: {e}")


def example_best_caption_track():
    """Example 7: Best Caption Track Selection (client-side)."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Best Caption Track Selection")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: `get_best_caption_track` was removed in 2.0. Pick a preferred track
    # from get.captions() results client-side (prefer manual over auto-generated).
    print("🎯 Finding best caption track...")
    try:
        caption_result = toolkit.get.captions(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        preferred_language = 'en'

        candidates = [t for t in caption_result.tracks
                      if t.language_code == preferred_language and t.is_accessible]
        # Prefer manual (human) tracks first, then any accessible track
        candidates.sort(key=lambda t: t.is_auto_generated)

        if candidates:
            best = candidates[0]
            print(f"✅ Best track found:")
            print(f"   Language: {best.language} ({best.language_code})")
            print(f"   Name: {best.name}")
            print(f"   Type: {best.track_type}")
            print(f"   Status: {best.status}")
            print(f"   Auto-generated: {best.is_auto_generated}")
            print(f"   CC: {best.is_cc}")
            print(f"   Display name: {best.display_name}")
        else:
            print("❌ No suitable caption track found")
    except Exception as e:
        print(f"❌ Best track selection failed: {e}")


def example_caption_filtering_advanced():
    """Example 8: Advanced Caption Filtering (client-side)."""
    print("\n" + "="*70)
    print("EXAMPLE 8: Advanced Caption Filtering")
    print("="*70)

    toolkit = setup_toolkit()

    # NOTE: CaptionFilters passed to list_captions was removed from the sub-API.
    # Fetch once with get.captions, then filter the CaptionTrack list locally.
    try:
        caption_result = toolkit.get.captions(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
    except Exception as e:
        print(f"❌ Could not list captions: {e}")
        return

    tracks = caption_result.tracks

    filter_tests = [
        ('Auto-generated only', [t for t in tracks if t.is_auto_generated]),
        ('Manual captions only', [t for t in tracks if t.is_manual]),
        ('CC captions only', [t for t in tracks if t.is_cc]),
        ('Accessible captions only', [t for t in tracks if t.is_accessible]),
        ('English and Spanish', [t for t in tracks if t.language_code in ('en', 'es')]),
    ]

    for name, filtered in filter_tests:
        print(f"\n🔍 Testing: {name}")
        print(f"   Found {len(filtered)} tracks")
        for track in filtered[:2]:
            print(f"   - {track.display_name} ({track.language_code})")
            print(f"     Type: {track.track_type}, Status: {track.status}")


def main():
    """Run all advanced caption examples."""
    print("YouTube Toolkit - Advanced Captions Examples")
    print("=" * 70)

    # Check if API key is available
    if not os.getenv("YOUTUBE_API_KEY"):
        print("⚠️  Warning: YOUTUBE_API_KEY not set. Some features may not work.")
        print("   Set your API key: export YOUTUBE_API_KEY='your_api_key_here'")
        print("   Get API key from: https://console.developers.google.com/")
        print()

    try:
        example_caption_listing()
        example_caption_download()
        example_caption_analysis()
        example_caption_search()
        example_caption_format_conversion()
        example_caption_export()
        example_best_caption_track()
        example_caption_filtering_advanced()

        print("\n" + "="*70)
        print("All advanced caption examples completed successfully!")
        print("="*70)

        print("\n🎯 Key Features Demonstrated:")
        print("  ✅ Caption listing (get.captions)")
        print("  ✅ Caption download (download.captions)")
        print("  ✅ Local caption analysis (CaptionAnalyzer)")
        print("  ✅ Client-side caption content search")
        print("  ✅ Format conversion (CaptionFormatConverter)")
        print("  ✅ Caption export via download in multiple formats")
        print("  ✅ Best caption track selection (client-side)")
        print("  ✅ Client-side caption filtering")
        print("\nℹ️  Removed in 2.0 (no sub-API): advanced_download_captions,")
        print("   get_caption_analytics, search_captions, export_captions,")
        print("   get_best_caption_track, get_captions_in_format.")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure you have:")
        print("1. Installed all dependencies: uv add google-api-python-client")
        print("2. Set your YouTube API key: export YOUTUBE_API_KEY='your_key'")
        print("3. Internet connection for API calls")


if __name__ == "__main__":
    main()
