#!/usr/bin/env python3
"""
YouTube Agent Quick Start Example

This example demonstrates how to build a YouTube agent using the youtube-toolkit
for caption retrieval, search, and content download.
"""

import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# Add the package to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'youtube_toolkit'))

from youtube_toolkit import YouTubeToolkit

class SimpleYouTubeAgent:
    """A simple YouTube agent demonstrating core capabilities."""
    
    def __init__(self, verbose: bool = True):
        """Initialize the agent."""
        self.toolkit = YouTubeToolkit(verbose=verbose)
        self.verbose = verbose
    
    def analyze_video(self, url: str) -> Dict[str, Any]:
        """Analyze a video comprehensively."""
        if self.verbose:
            print(f"\n🔍 Analyzing video: {url}")
        
        results = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'metadata': {},
            'captions': {},
            'similar_videos': [],
            'analysis': {}
        }
        
        try:
            # 1. Get video metadata
            if self.verbose:
                print("📊 Extracting metadata...")
            results['metadata'] = self._get_video_metadata(url)
            
            # 2. Get captions
            if self.verbose:
                print("📝 Retrieving captions...")
            results['captions'] = self._get_captions(url)
            
            # 3. Search for similar videos
            if self.verbose:
                print("🔍 Searching for similar videos...")
            results['similar_videos'] = self._search_similar_videos(url)
            
            # 4. Analyze content
            if self.verbose:
                print("🧠 Analyzing content...")
            results['analysis'] = self._analyze_content(results)
            
            results['status'] = 'success'
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            if self.verbose:
                print(f"❌ Error: {e}")
        
        return results
    
    def _get_video_metadata(self, url: str) -> Dict[str, Any]:
        """Get video metadata."""
        try:
            # get.video(url) returns a VideoInfo dataclass (attribute access)
            info = self.toolkit.get.video(url)
            description = info.description or ''
            return {
                'title': info.title or 'Unknown',
                'description': description[:200] + '...' if len(description) > 200 else description,
                'channel': info.author or 'Unknown',
                'views': info.views or 0,
                'likes': info.like_count or 0,
                'duration': info.duration or 0,
                'published': info.published_date or 'Unknown'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_captions(self, url: str) -> Dict[str, Any]:
        """Get video captions with analysis."""
        try:
            # List available captions -> get.captions returns a CaptionResult
            caption_result = self.toolkit.get.captions(url)
            available_languages = [track.language for track in caption_result.tracks]

            # Download English captions to disk. NOTE: advanced_download_captions
            # (which returned an analysis payload) was removed in 2.0;
            # download.captions returns the output file path, and we derive the
            # word count locally from the downloaded file.
            from youtube_toolkit import CaptionFormatConverter

            file_path = self.toolkit.download.captions(url, lang='en', format='srt')

            with open(file_path, 'r', encoding='utf-8') as f:
                cues = CaptionFormatConverter.parse_srt(f.read())

            word_count = sum(len(cue.text.split()) for cue in cues)
            total_duration = max((cue.end_time for cue in cues), default=0)

            return {
                'status': 'success',
                'available_languages': available_languages,
                'downloaded_language': 'en',
                'file_path': file_path,
                'word_count': word_count,
                'duration': total_duration,
                'cue_count': len(cues)
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _search_similar_videos(self, url: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar videos."""
        try:
            # Get video metadata to use for search
            metadata = self._get_video_metadata(url)
            title = metadata.get('title', '')
            
            if not title or title == 'Unknown':
                return []
            
            # Search for similar content. search.videos returns a list of dicts
            # with keys: title, author, views, length, watch_url, publish_date.
            results = self.toolkit.search.videos(title, limit=max_results)

            # Format results
            similar_videos = []
            for video in results:
                similar_videos.append({
                    'title': video.get('title', 'Unknown'),
                    'channel': video.get('author', 'Unknown'),
                    'views': video.get('views', 0),
                    'duration': video.get('length', 0),
                    'url': video.get('watch_url', ''),
                    'published': video.get('publish_date', 'Unknown')
                })

            return similar_videos
            
        except Exception as e:
            return []
    
    def _analyze_content(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze video content."""
        analysis = {
            'content_type': 'unknown',
            'complexity_score': 5,
            'engagement_level': 'medium',
            'educational_value': 5,
            'summary': 'Analysis not available'
        }
        
        try:
            metadata = results.get('metadata', {})
            captions = results.get('captions', {})
            
            # Determine content type
            title = metadata.get('title', '').lower()
            if any(word in title for word in ['tutorial', 'how to', 'learn', 'course']):
                analysis['content_type'] = 'educational'
            elif any(word in title for word in ['review', 'comparison', 'vs']):
                analysis['content_type'] = 'review'
            elif any(word in title for word in ['news', 'update', 'breaking']):
                analysis['content_type'] = 'news'
            else:
                analysis['content_type'] = 'entertainment'
            
            # Calculate complexity score
            if captions.get('status') == 'success':
                word_count = captions.get('word_count', 0)
                duration = captions.get('duration', 0)
                
                if duration > 0:
                    words_per_minute = word_count / (duration / 60)
                    if words_per_minute > 200:
                        analysis['complexity_score'] = 8
                    elif words_per_minute > 150:
                        analysis['complexity_score'] = 6
                    else:
                        analysis['complexity_score'] = 4
            
            # Assess engagement level
            views = metadata.get('views', 0)
            if views > 1000000:
                analysis['engagement_level'] = 'high'
            elif views > 100000:
                analysis['engagement_level'] = 'medium'
            else:
                analysis['engagement_level'] = 'low'
            
            # Assess educational value
            if analysis['content_type'] == 'educational':
                analysis['educational_value'] = 8
            elif analysis['content_type'] == 'review':
                analysis['educational_value'] = 6
            else:
                analysis['educational_value'] = 4
            
            # Generate summary
            analysis['summary'] = self._generate_summary(metadata, captions)
            
        except Exception as e:
            analysis['error'] = str(e)
        
        return analysis
    
    def _generate_summary(self, metadata: Dict, captions: Dict) -> str:
        """Generate a simple summary."""
        title = metadata.get('title', 'Unknown')
        channel = metadata.get('channel', 'Unknown')
        views = metadata.get('views', 0)
        word_count = captions.get('word_count', 0)
        
        summary = f"This video '{title}' by {channel} has {views:,} views"
        
        if word_count > 0:
            summary += f" and contains {word_count} words of content"
        
        if captions.get('status') == 'success':
            summary += ". Captions are available for analysis."
        else:
            summary += ". Captions are not available."
        
        return summary
    
    def download_content(self, url: str, content_type: str = 'audio', format: str = 'mp3') -> Dict[str, Any]:
        """Download video or audio content."""
        if self.verbose:
            print(f"\n📥 Downloading {content_type} from: {url}")
        
        try:
            # download.video / download.audio return the output file path (str)
            if content_type == 'video':
                file_path = self.toolkit.download.video(url, quality='best')
            elif content_type == 'audio':
                file_path = self.toolkit.download.audio(url, format=format)
            else:
                return {'status': 'error', 'error': 'Invalid content type. Use "video" or "audio"'}

            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 'Unknown'
            return {
                'status': 'success',
                'content_type': content_type,
                'format': format,
                'file_path': file_path,
                'file_size': file_size
            }

        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def search_and_analyze(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search for videos and analyze the top result."""
        if self.verbose:
            print(f"\n🔍 Searching for: {query}")
        
        try:
            # Search for videos (search.videos returns list of dicts)
            results = self.toolkit.search.videos(query, limit=max_results)

            if not results:
                return {'status': 'error', 'error': 'No videos found'}

            # Analyze the first result
            top_video = results[0]
            video_url = top_video.get('watch_url', '')
            
            if not video_url:
                return {'status': 'error', 'error': 'No valid URL found'}
            
            # Analyze the video
            analysis = self.analyze_video(video_url)
            
            return {
                'status': 'success',
                'query': query,
                'search_results': len(results),
                'top_video_analysis': analysis,
                'all_results': results
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

def main():
    """Main function demonstrating the YouTube agent."""
    print("🤖 YouTube Agent Example")
    print("=" * 50)
    
    # Initialize agent
    agent = SimpleYouTubeAgent(verbose=True)
    
    # Example 1: Analyze a specific video
    print("\n📹 Example 1: Video Analysis")
    print("-" * 30)
    
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    analysis = agent.analyze_video(video_url)
    
    if analysis['status'] == 'success':
        print(f"✅ Analysis completed successfully!")
        print(f"Title: {analysis['metadata']['title']}")
        print(f"Channel: {analysis['metadata']['channel']}")
        print(f"Views: {analysis['metadata']['views']:,}")
        print(f"Content Type: {analysis['analysis']['content_type']}")
        print(f"Complexity Score: {analysis['analysis']['complexity_score']}/10")
        print(f"Educational Value: {analysis['analysis']['educational_value']}/10")
        
        if analysis['captions']['status'] == 'success':
            print(f"Captions: ✅ Available ({analysis['captions']['word_count']} words)")
        else:
            print(f"Captions: ❌ {analysis['captions'].get('error', 'Not available')}")
    else:
        print(f"❌ Analysis failed: {analysis.get('error', 'Unknown error')}")
    
    # Example 2: Search and analyze
    print("\n🔍 Example 2: Search and Analyze")
    print("-" * 30)
    
    search_query = "python programming tutorial"
    search_result = agent.search_and_analyze(search_query, max_results=3)
    
    if search_result['status'] == 'success':
        print(f"✅ Found {search_result['search_results']} videos for '{search_query}'")
        top_analysis = search_result['top_video_analysis']
        if top_analysis['status'] == 'success':
            print(f"Top result: {top_analysis['metadata']['title']}")
            print(f"Channel: {top_analysis['metadata']['channel']}")
            print(f"Views: {top_analysis['metadata']['views']:,}")
    else:
        print(f"❌ Search failed: {search_result.get('error', 'Unknown error')}")
    
    # Example 3: Download content (commented out to avoid large downloads)
    print("\n📥 Example 3: Content Download")
    print("-" * 30)
    print("💡 Download functionality is available but commented out to avoid large files")
    print("   Uncomment the following lines to test downloads:")
    print("   # download_result = agent.download_content(video_url, 'audio', 'mp3')")
    print("   # print(f'Download: {download_result}')")
    
    print("\n🎉 YouTube Agent example completed!")
    print("Check the generated files for detailed results.")

if __name__ == "__main__":
    main()