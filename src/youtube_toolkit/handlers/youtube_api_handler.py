"""YouTube API handler for YouTube Toolkit.

This handler implements rich metadata extraction using the official YouTube Data API v3.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv


def _load_env_files():
    """Load .env files from multiple locations."""
    # Try to load from current working directory
    load_dotenv()

    # Also try common locations if API key not found yet
    if not os.getenv("YOUTUBE_API_KEY"):
        # Try home directory
        home_env = Path.home() / ".env"
        if home_env.exists():
            load_dotenv(home_env)

        # Try project root (look for .env in parent directories)
        current = Path.cwd()
        for parent in [current] + list(current.parents)[:3]:  # Check up to 3 levels
            env_file = parent / ".env"
            if env_file.exists():
                load_dotenv(env_file)
                break


# Load environment variables from .env files
_load_env_files()


class YouTubeAPIHandler:
    """Handler for YouTube Data API v3 functionality."""
    
    def __init__(self):
        """Initialize the YouTube API handler."""
        self._youtube = None
        self._initialized = False
        self._api_key = None
    
    def _ensure_initialized(self):
        """Ensure YouTube API is available and initialized."""
        if not self._initialized:
            try:
                from googleapiclient.discovery import build
                
                # Get API key from environment
                self._api_key = os.getenv("YOUTUBE_API_KEY")
                if not self._api_key:
                    raise ValueError("YOUTUBE_API_KEY environment variable is not set")
                
                self._youtube = build('youtube', 'v3', developerKey=self._api_key)
                self._initialized = True
                
            except ImportError:
                raise ImportError("google-api-python-client is not installed. Install with: uv add google-api-python-client")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize YouTube API: {e}")
    
    def parse_url(self, video_url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Video ID string
        """
        if 'v=' in video_url:
            video_id = video_url.split('v=')[1]
            if '&' in video_id:
                video_id = video_id.split('&')[0]
        elif 'youtu.be/' in video_url:
            video_id = video_url.split('youtu.be/')[1].split('?')[0]
        else:
            raise ValueError("Invalid YouTube URL format")
        
        return video_id
    
    def fetch_metadata(self, video_url: str) -> Dict[str, Any]:
        """
        Fetch rich metadata for a given YouTube video URL using the official API.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Dictionary with comprehensive video metadata
        """
        self._ensure_initialized()
        
        try:
            video_id = self.parse_url(video_url)
            response = self._youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            ).execute()

            if not response["items"]:
                return {"error": "Video not found or invalid ID"}

            video = response["items"][0]
            snippet = video["snippet"]
            statistics = video.get("statistics", {})
            content_details = video.get("contentDetails", {})

            return {
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "channelTitle": snippet.get("channelTitle"),
                "publishedAt": snippet.get("publishedAt"),
                "tags": snippet.get("tags", []),
                "categoryId": snippet.get("categoryId"),
                "duration": content_details.get("duration"),
                "viewCount": int(statistics.get("viewCount", 0)),
                "likeCount": int(statistics.get("likeCount", 0)),
                "commentCount": int(statistics.get("commentCount", 0)),
                "videoId": video_id,
                "videoUrl": video_url
            }
            
        except Exception as e:
            return {"error": f"Failed to fetch metadata: {e}"}
    
    def search_videos(self, query: str, max_results: int = 20, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos using the official YouTube Data API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (max 50)
            filters: Optional search filters (legacy compatibility)
            
        Returns:
            List of video dictionaries with search results
        """
        self._ensure_initialized()
        
        try:
            # Limit max_results to API maximum
            max_results = min(max_results, 50)
            
            response = self._youtube.search().list(
                part='snippet',
                q=query,
                type='video',
                maxResults=max_results,
                order='relevance'
            ).execute()
            
            results = []
            
            for item in response.get('items', []):
                try:
                    snippet = item['snippet']
                    video_id = item['id']['videoId']
                    
                    # Get additional video details
                    video_response = self._youtube.videos().list(
                        part='contentDetails,statistics',
                        id=video_id
                    ).execute()
                    
                    video_details = video_response.get('items', [{}])[0]
                    content_details = video_details.get('contentDetails', {})
                    statistics = video_details.get('statistics', {})
                    
                    results.append({
                        'title': snippet.get('title', 'Unknown Title'),
                        'watch_url': f"https://www.youtube.com/watch?v={video_id}",
                        'video_id': video_id,
                        'author': snippet.get('channelTitle', 'Unknown Author'),
                        'length': self._parse_duration(content_details.get('duration', 'PT0S')),
                        'views': int(statistics.get('viewCount', 0)),
                        'publish_date': snippet.get('publishedAt'),
                        'description': snippet.get('description', '')[:200] + "..." if len(snippet.get('description', '')) > 200 else snippet.get('description', '')
                    })
                    
                except Exception as video_error:
                    print(f"Warning: Failed to process search result: {video_error}")
                    continue
            
            return results
            
        except Exception as e:
            return []
    
    def _build_api_search_params(self, filters, query, max_results):
        """Build the YouTube Data API ``search().list`` parameter dict from filters."""
        # Build search parameters
        search_params = {
            'part': 'snippet',
            'q': query,
            'maxResults': max_results,
            'order': filters.order
        }

        # FIXED: Always add type filtering - YouTube API requires explicit type=video for video-specific filters
        search_params['type'] = filters.type

        # Add channel filtering
        if filters.channel_id:
            search_params['channelId'] = filters.channel_id
        if filters.channel_type:
            search_params['channelType'] = filters.channel_type

        # Add date filtering
        if filters.published_after:
            search_params['publishedAfter'] = filters.published_after.isoformat() + 'Z'
        if filters.published_before:
            search_params['publishedBefore'] = filters.published_before.isoformat() + 'Z'

        # Add video-specific filters
        if filters.video_duration:
            search_params['videoDuration'] = filters.video_duration
        if filters.video_definition:
            search_params['videoDefinition'] = filters.video_definition
        if filters.video_dimension:
            search_params['videoDimension'] = filters.video_dimension
        if filters.video_caption:
            search_params['videoCaption'] = filters.video_caption
        if filters.video_license:
            search_params['videoLicense'] = filters.video_license
        if filters.video_embeddable:
            search_params['videoEmbeddable'] = filters.video_embeddable
        if filters.video_syndicated:
            search_params['videoSyndicated'] = filters.video_syndicated
        if filters.video_type:
            search_params['videoType'] = filters.video_type

        # NEW: Event type filtering
        if filters.event_type:
            search_params['eventType'] = filters.event_type

        # NEW: Content ownership filtering
        if filters.for_content_owner:
            search_params['forContentOwner'] = 'true'
        if filters.for_developer:
            search_params['forDeveloper'] = 'true'
        if filters.for_mine:
            search_params['forMine'] = 'true'
        if filters.on_behalf_of_content_owner:
            search_params['onBehalfOfContentOwner'] = filters.on_behalf_of_content_owner

        # NEW: Video category filtering
        if filters.video_category_id:
            search_params['videoCategoryId'] = filters.video_category_id

        # NEW: Paid promotion filtering
        if filters.video_paid_product_placement:
            search_params['videoPaidProductPlacement'] = filters.video_paid_product_placement

        # NEW: Topic filtering
        if filters.topic_id:
            search_params['topicId'] = filters.topic_id

        # Add location and language filters
        if filters.location:
            search_params['location'] = filters.location
        if filters.location_radius:
            search_params['locationRadius'] = filters.location_radius
        if filters.relevance_language:
            search_params['relevanceLanguage'] = filters.relevance_language

        # Add region and safety filters
        if filters.region_code:
            search_params['regionCode'] = filters.region_code
        if filters.safe_search:
            search_params['safeSearch'] = filters.safe_search

        # NEW: Pagination support
        if filters.page_token:
            search_params['pageToken'] = filters.page_token

        # Use max_results from filters
        search_params['maxResults'] = filters.max_results

        return search_params

    def _process_api_search_results(self, response, query, filters,
                                    SearchResult, SearchResultItem,
                                    Thumbnails, Thumbnail, datetime):
        """Convert a YouTube Data API search response into the result dict."""
        # Process results
        items = []
        for item in response.get('items', []):
            try:
                snippet = item['snippet']
                item_id = item['id']

                # Determine resource type and extract ID
                kind = item_id.get('kind', 'youtube#video')
                video_id = item_id.get('videoId')
                channel_id = item_id.get('channelId')
                playlist_id = item_id.get('playlistId')

                # Parse thumbnails
                thumbnails_data = snippet.get('thumbnails', {})
                thumbnails = Thumbnails(
                    default=Thumbnail(**thumbnails_data['default']) if thumbnails_data.get('default') else None,
                    medium=Thumbnail(**thumbnails_data['medium']) if thumbnails_data.get('medium') else None,
                    high=Thumbnail(**thumbnails_data['high']) if thumbnails_data.get('high') else None,
                    standard=Thumbnail(**thumbnails_data['standard']) if thumbnails_data.get('standard') else None,
                    maxres=Thumbnail(**thumbnails_data['maxres']) if thumbnails_data.get('maxres') else None,
                )

                # Parse published date
                published_at = None
                if snippet.get('publishedAt'):
                    try:
                        published_at = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))
                    except:
                        pass

                # Create search result item
                search_item = SearchResultItem(
                    kind=kind,
                    etag=item.get('etag', ''),
                    video_id=video_id,
                    channel_id=channel_id,
                    playlist_id=playlist_id,
                    title=snippet.get('title', ''),
                    description=snippet.get('description', ''),
                    channel_title=snippet.get('channelTitle', ''),
                    published_at=published_at,
                    thumbnails=thumbnails,
                    live_broadcast_content=snippet.get('liveBroadcastContent', 'none')
                )

                items.append(search_item)

            except Exception as item_error:
                print(f"Warning: Failed to process search item: {item_error}")
                continue

        # Create comprehensive search result with quota information
        search_result = SearchResult(
            items=items,
            total_results=response.get('pageInfo', {}).get('totalResults', len(items)),
            query=query,
            filters_applied=filters,
            backend_used='youtube_api',
            next_page_token=response.get('nextPageToken'),
            prev_page_token=response.get('prevPageToken')
        )

        result_dict = search_result.to_dict()

        # Add quota and API information
        result_dict['quota_cost'] = 100  # YouTube Search API costs 100 quota units
        result_dict['api_info'] = {
            'region_code': response.get('regionCode'),
            'page_info': response.get('pageInfo', {}),
            'etag': response.get('etag'),
            'kind': response.get('kind')
        }

        return result_dict

    def advanced_search(self, query: str, filters: Optional[Dict] = None, max_results: int = 20) -> Dict[str, Any]:
        """
        Advanced search using YouTube Data API with comprehensive filtering and results.
        
        Args:
            query: Search query string
            filters: SearchFilters object with advanced filtering options
            max_results: Maximum number of results to return (max 50)
            
        Returns:
            Dictionary with comprehensive search results including thumbnails, live content, etc.
        """
        self._ensure_initialized()
        
        try:
            from ..core.search import SearchResult, SearchResultItem, SearchFilters, Thumbnails, Thumbnail
            from datetime import datetime
            
            # Use provided filters or create default
            if filters is None:
                filters = SearchFilters()
            elif isinstance(filters, dict):
                # Convert dict to SearchFilters object
                filters = SearchFilters(**filters)
            
            # Limit max_results to API maximum
            max_results = min(max_results, 50)

            # Build search parameters from the filters
            search_params = self._build_api_search_params(filters, query, max_results)

            # Validate filters before making request
            validation_errors = filters.validate_filters()
            if validation_errors:
                return {
                    'items': [],
                    'total_results': 0,
                    'query': query,
                    'error': f"Filter validation errors: {'; '.join(validation_errors)}",
                    'backend_used': 'youtube_api'
                }
            
            # Execute search
            response = self._youtube.search().list(**search_params).execute()

            # Process the API response into the result dict
            return self._process_api_search_results(
                response, query, filters,
                SearchResult, SearchResultItem, Thumbnails, Thumbnail, datetime
            )

        except Exception as e:
            # FIXED: Don't fall back - raise the error as requested by user
            raise RuntimeError(f"Advanced search failed: {e}")
    
    def _parse_duration(self, duration: str) -> int:
        """
        Parse ISO 8601 duration string to seconds.
        
        Args:
            duration: ISO 8601 duration string (e.g., "PT4M13S")
            
        Returns:
            Duration in seconds
        """
        try:
            import re
            
            # Parse ISO 8601 duration format
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                return hours * 3600 + minutes * 60 + seconds
            return 0
        except:
            return 0
    
    def get_playlist_urls(self, playlist_url: str) -> List[str]:
        """
        Extract video URLs from playlist using YouTube Data API.
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            List of video URLs
        """
        self._ensure_initialized()
        
        try:
            playlist_id = self._extract_playlist_id(playlist_url)
            if not playlist_id:
                print("❌ Could not extract playlist ID from URL")
                return []
            
            video_urls = []
            next_page_token = None
            
            while True:
                request = self._youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()
                
                for item in response['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    video_url = f'https://www.youtube.com/watch?v={video_id}'
                    video_urls.append(video_url)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
            
            if video_urls:
                print(f"✅ YouTube API playlist: {len(video_urls)} videos found")
                return video_urls
            else:
                print("⚠️  YouTube API playlist: No videos found")
                return []
                
        except Exception as e:
            print(f"❌ YouTube API playlist failed: {e}")
            return []
    
    def get_playlist_info(self, playlist_url: str) -> Dict[str, Any]:
        """
        Get basic playlist information.
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            Dictionary with playlist info
        """
        self._ensure_initialized()
        
        try:
            playlist_id = self._extract_playlist_id(playlist_url)
            if not playlist_id:
                return {
                    'title': 'YouTube Playlist',
                    'description': 'Playlist downloaded with YouTube Toolkit'
                }
            
            request = self._youtube.playlists().list(
                part='snippet',
                id=playlist_id
            )
            response = request.execute()
            
            if response['items']:
                playlist = response['items'][0]
                snippet = playlist['snippet']
                return {
                    'title': snippet.get('title', 'YouTube Playlist'),
                    'description': snippet.get('description', 'Playlist downloaded with YouTube Toolkit')
                }
            else:
                return {
                    'title': 'YouTube Playlist',
                    'description': 'Playlist downloaded with YouTube Toolkit'
                }
                
        except Exception as e:
            print(f"❌ YouTube API playlist info failed: {e}")
            return {
                'title': 'YouTube Playlist',
                'description': 'Playlist downloaded with YouTube Toolkit'
            }
    
    def _extract_playlist_id(self, playlist_url: str) -> str:
        """
        Extract playlist ID from YouTube playlist URL.
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            Playlist ID string
        """
        if 'list=' in playlist_url:
            playlist_id = playlist_url.split('list=')[1]
            if '&' in playlist_id:
                playlist_id = playlist_id.split('&')[0]
            return playlist_id
        else:
            return ""
    
    def download_captions(self, url: str, language_code: str = 'en', 
                          output_path: str = None) -> str:
        """
        Download captions using YouTube Data API (legacy method for backward compatibility).
        
        Args:
            url: YouTube video URL
            language_code: Language code (e.g., 'en', 'es', 'fr')
            output_path: Output file path (optional)
            
        Returns:
            Path to downloaded caption file
        """
        self._ensure_initialized()
        
        try:
            # Extract video ID
            video_id = self.extract_video_id(url)
            if not video_id:
                raise RuntimeError("Could not extract video ID from URL")
            
            # Get available caption tracks
            captions_request = self._youtube.captions().list(
                part='snippet',
                videoId=video_id
            )
            captions_response = captions_request.execute()
            
            if not captions_response.get('items'):
                raise RuntimeError("No captions available for this video")
            
            # Find caption track in requested language
            caption_id = None
            for item in captions_response['items']:
                snippet = item['snippet']
                if snippet.get('language') == language_code:
                    caption_id = item['id']
                    break
            
            # Fallback to first available caption
            if not caption_id:
                caption_id = captions_response['items'][0]['id']
                print(f"Language '{language_code}' not available. Using first available caption.")
            
            # Determine output path
            if not output_path:
                output_path = f"{video_id}_captions_{language_code}.txt"
            
            # Download caption content
            caption_request = self._youtube.captions().download(
                id=caption_id,
                tfmt='srt'  # SubRip format
            )
            
            # Save caption to file
            with open(output_path, 'wb') as f:
                f.write(caption_request.execute())
            
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to download captions with YouTube API: {e}")
    
    def advanced_list_captions(self, video_url: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Advanced caption listing with comprehensive filtering and metadata.
        
        Args:
            video_url: YouTube video URL
            filters: CaptionFilters object or dict with advanced filtering options
            
        Returns:
            Dictionary with comprehensive caption track information
        """
        self._ensure_initialized()
        
        try:
            from ..core.captions import (
                CaptionResult, CaptionFilters, CaptionTrack, CaptionTrackType,
                CaptionStatus, CaptionAnalytics
            )
            from datetime import datetime
            
            # Use provided filters or create default
            if filters is None:
                filters = CaptionFilters()
            elif isinstance(filters, dict):
                filters = CaptionFilters(**filters)
            
            # Validate filters
            validation_errors = filters.validate_filters()
            if validation_errors:
                return {
                    'tracks': [],
                    'error': f"Filter validation errors: {'; '.join(validation_errors)}",
                    'quota_cost': 50
                }
            
            video_id = self.parse_url(video_url)
            
            # Build caption list request parameters
            request_params = {
                'part': ['id', 'snippet'],
                'videoId': video_id
            }
            
            # Execute caption list request
            response = self._youtube.captions().list(**request_params).execute()
            
            # Process caption tracks
            tracks = []
            language_counts = {}
            auto_generated_count = 0
            manual_count = 0
            accessible_count = 0
            
            for item in response.get('items', []):
                try:
                    snippet = item['snippet']
                    
                    # Parse track type
                    track_type = CaptionTrackType.STANDARD
                    if snippet.get('trackKind') == 'asr':
                        track_type = CaptionTrackType.ASR
                    
                    # Parse status
                    status = CaptionStatus.SERVING
                    if snippet.get('status') == 'syncing':
                        status = CaptionStatus.SYNCING
                    elif snippet.get('status') == 'failed':
                        status = CaptionStatus.FAILED
                    
                    # Create caption track
                    track = CaptionTrack(
                        caption_id=item['id'],
                        language=snippet.get('name', ''),
                        language_code=snippet.get('language', ''),
                        name=snippet.get('name', ''),
                        track_type=track_type,
                        status=status,
                        is_auto_generated=snippet.get('trackKind') == 'asr',
                        is_cc=snippet.get('isCC', False),
                        is_draft=snippet.get('isDraft', False),
                        is_easy_reader=snippet.get('isEasyReader', False),
                        is_large=snippet.get('isLarge', False),
                        last_updated=self._parse_datetime(snippet['lastUpdated']) if snippet.get('lastUpdated') else None
                    )
                    
                    # Apply filters
                    if self._apply_caption_filters(track, filters):
                        tracks.append(track)
                        
                        # Update statistics
                        if track.is_accessible:
                            accessible_count += 1
                        if track.is_auto_generated:
                            auto_generated_count += 1
                        else:
                            manual_count += 1
                        
                        # Track language distribution
                        lang = track.language_code
                        language_counts[lang] = language_counts.get(lang, 0) + 1
                
                except Exception as track_error:
                    print(f"Warning: Failed to process caption track: {track_error}")
                    continue
            
            # Create analytics
            analytics = CaptionAnalytics(
                total_tracks=len(tracks),
                available_tracks=accessible_count,
                auto_generated_tracks=auto_generated_count,
                manual_tracks=manual_count,
                languages=list(language_counts.keys()),
                language_distribution=language_counts
            )
            
            # Create comprehensive result
            result = CaptionResult(
                tracks=tracks,
                analytics=analytics,
                filters_applied=filters,
                quota_cost=50
            )
            
            return result.to_dict()
            
        except Exception as e:
            print(f"Advanced caption listing failed: {e}")
            return {
                'tracks': [],
                'error': str(e),
                'quota_cost': 50
            }
    
    def advanced_download_captions(self, video_url: str, caption_id: Optional[str] = None,
                                 language_code: str = 'en', format: str = 'srt',
                                 output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Advanced caption download with format conversion and analysis.
        
        Args:
            video_url: YouTube video URL
            caption_id: Specific caption track ID (optional)
            language_code: Language code (e.g., 'en', 'es', 'fr')
            format: Output format ('srt', 'vtt', 'txt', 'ttml')
            output_path: Output file path (optional)
            
        Returns:
            Dictionary with download results and analysis
        """
        self._ensure_initialized()
        
        try:
            from ..core.captions import (
                CaptionContent, CaptionCue, CaptionFormat, CaptionFormatConverter,
                CaptionAnalyzer
            )
            from datetime import datetime
            
            video_id = self.parse_url(video_url)
            
            # If no caption_id provided, find the best track
            if not caption_id:
                caption_list = self.advanced_list_captions(video_url)
                tracks = caption_list.get('tracks', [])
                
                # Find best track
                best_track = None
                for track_data in tracks:
                    if track_data.get('language_code') == language_code and track_data.get('status') == 'serving':
                        best_track = track_data
                        break
                
                if not best_track:
                    # Fall back to first available track
                    best_track = tracks[0] if tracks else None
                
                if not best_track:
                    raise RuntimeError(f"No captions available for language '{language_code}'")
                
                caption_id = best_track['caption_id']
                language_code = best_track['language_code']
            
            # Download caption content
            try:
                caption_request = self._youtube.captions().download(
                    id=caption_id,
                    tfmt='srt'  # Always download as SRT first
                )
                
                raw_content = caption_request.execute().decode('utf-8')
            except Exception as api_error:
                # If YouTube API fails (e.g., requires OAuth2), fall back to other methods
                raise RuntimeError(f"YouTube API caption download requires OAuth2 authentication. Error: {api_error}")
            
            # Parse SRT content
            cues = CaptionFormatConverter.parse_srt(raw_content)
            
            # Create caption content object
            caption_content = CaptionContent(
                caption_id=caption_id,
                language=language_code,
                language_code=language_code,
                cues=cues,
                format=CaptionFormat.SRT,
                raw_content=raw_content
            )
            
            # Convert format if needed
            converted_content = raw_content
            if format.lower() == 'vtt':
                converted_content = CaptionFormatConverter.srt_to_vtt(raw_content)
            elif format.lower() == 'txt':
                converted_content = CaptionFormatConverter.srt_to_txt(raw_content)
            
            # Generate output path if not provided
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"{video_id}_captions_{language_code}_{timestamp}.{format}"
            
            # Save caption to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(converted_content)
            
            # Perform analysis
            analysis = {
                'total_duration': caption_content.total_duration,
                'word_count': caption_content.word_count,
                'cue_count': caption_content.cue_count,
                'average_cue_duration': caption_content.average_cue_duration,
                'words_per_minute': CaptionAnalyzer.analyze_reading_speed(cues)['average_wpm'],
                'language_analysis': CaptionAnalyzer.analyze_language(converted_content),
                'gaps': CaptionAnalyzer.find_gaps(cues)
            }
            
            return {
                'success': True,
                'output_path': output_path,
                'caption_id': caption_id,
                'language_code': language_code,
                'format': format,
                'content': caption_content,
                'analysis': analysis,
                'quota_cost': 50
            }
            
        except Exception as e:
            # Re-raise the exception so the main toolkit can handle fallback
            raise e
    
    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string with proper handling of microseconds."""
        try:
            # Remove Z and replace with +00:00
            datetime_str = datetime_str.replace('Z', '+00:00')
            
            # Handle microseconds with more than 6 digits
            if '.' in datetime_str and '+' in datetime_str:
                base_part, tz_part = datetime_str.split('+')
                if '.' in base_part:
                    date_part, micro_part = base_part.split('.')
                    # Truncate microseconds to 6 digits
                    micro_part = micro_part[:6]
                    datetime_str = f"{date_part}.{micro_part}+{tz_part}"
            
            return datetime.fromisoformat(datetime_str)
        except Exception:
            return None
    
    def _apply_caption_filters(self, track: 'CaptionTrack', filters: 'CaptionFilters') -> bool:
        """Apply filters to a caption track."""
        # Language filtering
        if filters.language_codes and track.language_code not in filters.language_codes:
            return False
        if filters.languages and track.language not in filters.languages:
            return False
        
        # Track type filtering
        if filters.track_types and track.track_type not in filters.track_types:
            return False
        if filters.auto_generated_only and not track.is_auto_generated:
            return False
        if filters.manual_only and track.is_auto_generated:
            return False
        
        # Status filtering
        if filters.statuses and track.status not in filters.statuses:
            return False
        if filters.accessible_only and not track.is_accessible:
            return False
        
        # Feature filtering
        if filters.cc_only and not track.is_cc:
            return False
        if filters.draft_only and not track.is_draft:
            return False
        if filters.easy_reader_only and not track.is_easy_reader:
            return False
        if filters.large_only and not track.is_large:
            return False
        
        return True
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID string
        """
        import re
        
        # YouTube URL patterns
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return ""
    
    def fetch_comments(self, video_url: str, max_results: int = 100,
                      reply_max_results: int = 20, order: str = 'relevance') -> List[Dict[str, Any]]:
        """
        Fetch comments from a YouTube video (legacy method for backward compatibility).
        
        Args:
            video_url: YouTube video URL
            max_results: Maximum number of comments to retrieve
            reply_max_results: Maximum number of replies per comment
            order: Comment order ('relevance', 'time', 'rating')
            
        Returns:
            List of comment threads with replies
        """
        self._ensure_initialized()
        
        try:
            video_id = self.parse_url(video_url)
            response = self._youtube.commentThreads().list(
                part=['snippet', 'replies'],
                videoId=video_id,
                order=order,
                maxResults=max_results
            ).execute()

            threads = []
            for item in response.get('items', []):
                top_snippet = item['snippet']['topLevelComment']['snippet']
                comment_id = item['snippet']['topLevelComment']['id']

                top_comment = {
                    'text': top_snippet['textDisplay'],
                    'likes': top_snippet['likeCount'],
                    'author': top_snippet['authorDisplayName'],
                    'published': top_snippet['publishedAt'],
                    'replies': self.fetch_replies(comment_id, max_results=reply_max_results)
                }

                threads.append(top_comment)

            return sorted(threads, key=lambda x: x['likes'], reverse=True)
            
        except Exception as e:
            print(f"Error fetching comments: {e}")
            return []
    
    def _process_comment_threads(self, response, filters, video_id,
                                 Comment, CommentAuthor, CommentMetrics, datetime):
        """Parse comment-thread API items into Comment objects with running stats.

        Returns a (comments, total_likes, total_replies, author_counts) tuple.
        """
        # Process comment threads
        comments = []
        total_likes = 0
        total_replies = 0
        author_counts = {}

        for item in response.get('items', []):
            try:
                # Parse top-level comment
                top_comment_data = item['snippet']['topLevelComment']
                snippet = top_comment_data['snippet']

                # Create comment author
                author = CommentAuthor(
                    display_name=snippet.get('authorDisplayName', 'Unknown'),
                    profile_image_url=snippet.get('authorProfileImageUrl'),
                    channel_id=snippet.get('authorChannelId', {}).get('value'),
                    channel_url=snippet.get('authorChannelUrl'),
                    is_verified=snippet.get('authorChannelVerified', False),
                    is_channel_owner=snippet.get('authorChannelVerified', False)
                )

                # Create comment metrics
                metrics = CommentMetrics(
                    like_count=snippet.get('likeCount', 0),
                    total_reply_count=item['snippet'].get('totalReplyCount', 0),
                    updated_at=datetime.fromisoformat(snippet['updatedAt'].replace('Z', '+00:00')) if snippet.get('updatedAt') else None
                )

                # Create comment
                comment = Comment(
                    comment_id=top_comment_data['id'],
                    text=snippet.get('textDisplay', ''),
                    author=author,
                    published_at=datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(snippet['updatedAt'].replace('Z', '+00:00')) if snippet.get('updatedAt') else None,
                    metrics=metrics,
                    video_id=video_id
                )

                # Process replies if requested
                if filters.include_replies and 'replies' in item:
                    replies_data = item['replies'].get('comments', [])
                    for reply_data in replies_data[:filters.max_replies_per_comment]:
                        reply_snippet = reply_data['snippet']

                        reply_author = CommentAuthor(
                            display_name=reply_snippet.get('authorDisplayName', 'Unknown'),
                            profile_image_url=reply_snippet.get('authorProfileImageUrl'),
                            channel_id=reply_snippet.get('authorChannelId', {}).get('value'),
                            channel_url=reply_snippet.get('authorChannelUrl')
                        )

                        reply_metrics = CommentMetrics(
                            like_count=reply_snippet.get('likeCount', 0)
                        )

                        reply = Comment(
                            comment_id=reply_data['id'],
                            text=reply_snippet.get('textDisplay', ''),
                            author=reply_author,
                            published_at=datetime.fromisoformat(reply_snippet['publishedAt'].replace('Z', '+00:00')),
                            metrics=reply_metrics,
                            parent_id=comment.comment_id,
                            video_id=video_id
                        )

                        comment.add_reply(reply)
                        total_replies += 1

                # Apply filters
                if self._apply_comment_filters(comment, filters):
                    comments.append(comment)
                    total_likes += comment.metrics.like_count

                    # Track author statistics
                    author_name = comment.author.display_name
                    author_counts[author_name] = author_counts.get(author_name, 0) + 1

            except Exception as comment_error:
                print(f"Warning: Failed to process comment: {comment_error}")
                continue

        return comments, total_likes, total_replies, author_counts

    def _build_comment_result(self, response, filters, comments, total_likes,
                              total_replies, author_counts,
                              CommentResult, CommentAnalytics, CommentSentimentAnalyzer):
        """Build comment analytics and the comprehensive result dict."""
        # Create analytics
        analytics = CommentAnalytics(
            total_comments=len(comments),
            total_replies=total_replies,
            total_likes=total_likes,
            unique_authors=len(author_counts),
            top_authors=[
                {'name': name, 'comment_count': count}
                for name, count in sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ],
            most_liked_comments=sorted(comments, key=lambda x: x.metrics.like_count, reverse=True)[:5],
            most_replied_comments=sorted(comments, key=lambda x: x.metrics.total_reply_count, reverse=True)[:5]
        )

        # Perform sentiment analysis if requested
        if len(comments) > 0:
            sentiment_scores = CommentSentimentAnalyzer.analyze_sentiment(
                ' '.join([comment.text for comment in comments[:50]])  # Analyze first 50 comments
            )
            analytics.sentiment_analysis = sentiment_scores

        # Create comprehensive result
        result = CommentResult(
            comments=comments,
            total_results=response.get('pageInfo', {}).get('totalResults', len(comments)),
            page_info=response.get('pageInfo', {}),
            next_page_token=response.get('nextPageToken'),
            prev_page_token=response.get('prevPageToken'),
            filters_applied=filters,
            analytics=analytics,
            quota_cost=1
        )

        return result.to_dict()

    def advanced_fetch_comments(self, video_url: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Advanced comment fetching with comprehensive filtering, pagination, and analytics.
        
        Args:
            video_url: YouTube video URL
            filters: CommentFilters object or dict with advanced filtering options
            
        Returns:
            Dictionary with comprehensive comment results including analytics
        """
        self._ensure_initialized()
        
        try:
            from ..core.comments import (
                CommentResult, CommentFilters, Comment, CommentAuthor, 
                CommentMetrics, CommentAnalytics, CommentSentimentAnalyzer
            )
            from datetime import datetime
            
            # Use provided filters or create default
            if filters is None:
                filters = CommentFilters()
            elif isinstance(filters, dict):
                filters = CommentFilters(**filters)
            
            # Validate filters
            validation_errors = filters.validate_filters()
            if validation_errors:
                return {
                    'comments': [],
                    'total_results': 0,
                    'error': f"Filter validation errors: {'; '.join(validation_errors)}",
                    'quota_cost': 1
                }
            
            video_id = self.parse_url(video_url)
            
            # Build comment thread request parameters
            thread_params = {
                'part': ['snippet', 'replies'],
                'videoId': video_id,
                'order': filters.order.value,
                'maxResults': min(filters.max_results, 100)
            }
            
            # Add pagination
            if filters.page_token:
                thread_params['pageToken'] = filters.page_token
            
            # Add text format
            if filters.text_format.value == 'plainText':
                thread_params['textFormat'] = 'plainText'
            
            # Execute comment threads request
            response = self._youtube.commentThreads().list(**thread_params).execute()

            # Process comment threads into Comment objects + running stats
            comments, total_likes, total_replies, author_counts = self._process_comment_threads(
                response, filters, video_id,
                Comment, CommentAuthor, CommentMetrics, datetime
            )

            # Build analytics + comprehensive result dict
            return self._build_comment_result(
                response, filters, comments, total_likes, total_replies, author_counts,
                CommentResult, CommentAnalytics, CommentSentimentAnalyzer
            )

        except Exception as e:
            print(f"Advanced comment fetch failed: {e}")
            return {
                'comments': [],
                'total_results': 0,
                'error': str(e),
                'quota_cost': 1
            }
    
    def _apply_comment_filters(self, comment: 'Comment', filters: 'CommentFilters') -> bool:
        """Apply filters to a comment."""
        # Date filtering
        if filters.published_after and comment.published_at < filters.published_after:
            return False
        if filters.published_before and comment.published_at > filters.published_before:
            return False
        
        # Engagement filtering
        if filters.min_likes and comment.metrics.like_count < filters.min_likes:
            return False
        if filters.min_replies and comment.metrics.total_reply_count < filters.min_replies:
            return False
        
        # Author filtering
        if filters.author_channel_id and comment.author.channel_id != filters.author_channel_id:
            return False
        
        # Search filtering
        if filters.search_terms and filters.search_terms.lower() not in comment.text.lower():
            return False
        
        return True
    
    def fetch_replies(self, comment_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch replies to a specific comment.
        
        Args:
            comment_id: YouTube comment ID
            max_results: Maximum number of replies to retrieve
            
        Returns:
            List of reply dictionaries
        """
        self._ensure_initialized()
        
        try:
            reply_response = self._youtube.comments().list(
                part='snippet',
                parentId=comment_id,
                maxResults=max_results,
                textFormat='plainText'
            ).execute()

            replies = [
                {
                    'text': r['snippet']['textDisplay'],
                    'likes': r['snippet']['likeCount'],
                    'author': r['snippet']['authorDisplayName'], 
                    'published': r['snippet']['publishedAt']
                }
                for r in reply_response.get('items', [])
            ]
            return sorted(replies, key=lambda x: x['likes'], reverse=True)
            
        except Exception as e:
            print(f"Error fetching replies: {e}")
            return []
    
    def process_url_comments(self, video_url: str, top_n: int = 3, 
                           comment_max: int = 100, reply_max: int = 20, 
                           order: str = 'relevance') -> List[Dict[str, Any]]:
        """
        Convenience method: Parse URL → Fetch Comments → Return Top N Threads
        
        Args:
            video_url: YouTube video URL
            top_n: Number of top comments to display
            comment_max: Maximum comments to fetch
            reply_max: Maximum replies per comment
            order: Comment order
            
        Returns:
            List of comment threads
        """
        threads = self.fetch_comments(
            video_url,
            max_results=comment_max,
            reply_max_results=reply_max,
            order=order
        )
        
        self.display_threads(threads, limit=top_n)
        
        return threads
    
    def display_threads(self, threads: List[Dict[str, Any]], limit: Optional[int] = None) -> None:
        """
        Display comment threads in a readable format.
        
        Args:
            threads: List of comment threads
            limit: Maximum number of threads to display
        """
        display_items = threads if limit is None else threads[:limit]
        
        for i, thread in enumerate(display_items, 1):
            print(f"\n{i}. 👍 {thread['likes']} | {thread['text'][:100]}... (by {thread['author']})")
            
            if thread['replies']:
                for reply in thread['replies'][:3]:  # Show first 3 replies
                    print(f"    ↳ 👍 {reply['likes']} | {reply['text'][:80]}... (by {reply['author']})")
                
                if len(thread['replies']) > 3:
                    print(f"    ... and {len(thread['replies']) - 3} more replies")
    
    def test_connection(self, video_url: str) -> bool:
        """
        Test if YouTube API can connect and fetch basic data.

        Args:
            video_url: YouTube video URL

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._ensure_initialized()
            metadata = self.fetch_metadata(video_url)
            return "error" not in metadata
        except Exception:
            return False

    # ==================== v0.7 ANALYTICAL FEATURES ====================

    # --- Subscriptions API ---

    def get_channel_subscriptions(self, channel_id: str, max_results: int = 50,
                                  order: str = 'relevance',
                                  page_token: str = None) -> Dict[str, Any]:
        """
        Get subscriptions of a channel (channels they are subscribed to).

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of results (max 50)
            order: Sort order ('alphabetical', 'relevance', 'unread')
            page_token: Token for pagination

        Returns:
            Dictionary with subscription data and pagination info
        """
        self._ensure_initialized()

        try:
            params = {
                'part': 'snippet,contentDetails',
                'channelId': channel_id,
                'maxResults': min(max_results, 50),
                'order': order,
            }

            if page_token:
                params['pageToken'] = page_token

            response = self._youtube.subscriptions().list(**params).execute()

            subscriptions = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                content_details = item.get('contentDetails', {})
                resource_id = snippet.get('resourceId', {})

                subscriptions.append({
                    'subscription_id': item.get('id', ''),
                    'channel_id': resource_id.get('channelId', ''),
                    'channel_title': snippet.get('title', ''),
                    'channel_description': snippet.get('description', ''),
                    'channel_thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                    'subscribed_at': snippet.get('publishedAt', ''),
                    'total_item_count': content_details.get('totalItemCount', 0),
                    'new_item_count': content_details.get('newItemCount', 0),
                    'activity_type': content_details.get('activityType', ''),
                })

            return {
                'subscriptions': subscriptions,
                'total_results': response.get('pageInfo', {}).get('totalResults', len(subscriptions)),
                'results_per_page': response.get('pageInfo', {}).get('resultsPerPage', max_results),
                'next_page_token': response.get('nextPageToken'),
                'prev_page_token': response.get('prevPageToken'),
                'quota_cost': 1,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to get channel subscriptions: {e}")

    def check_subscription(self, channel_id: str, target_channel_id: str) -> Dict[str, Any]:
        """
        Check if a channel is subscribed to another channel.

        Args:
            channel_id: The channel to check subscriptions for
            target_channel_id: The channel to check if subscribed to

        Returns:
            Dictionary with subscription status and details
        """
        self._ensure_initialized()

        try:
            response = self._youtube.subscriptions().list(
                part='snippet',
                channelId=channel_id,
                forChannelId=target_channel_id
            ).execute()

            if response.get('items'):
                item = response['items'][0]
                snippet = item.get('snippet', {})
                return {
                    'is_subscribed': True,
                    'subscription_id': item.get('id', ''),
                    'subscribed_at': snippet.get('publishedAt', ''),
                    'channel_title': snippet.get('title', ''),
                }
            else:
                return {
                    'is_subscribed': False,
                    'subscription_id': None,
                    'subscribed_at': None,
                    'channel_title': None,
                }

        except Exception as e:
            raise RuntimeError(f"Failed to check subscription: {e}")

    # --- Video Categories API ---

    def get_video_categories(self, region_code: str = 'US',
                            language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get video categories available in a region.

        Args:
            region_code: ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'JP')
            language: Language for category names (e.g., 'en', 'es', 'ja')

        Returns:
            List of video category dictionaries
        """
        self._ensure_initialized()

        try:
            response = self._youtube.videoCategories().list(
                part='snippet',
                regionCode=region_code,
                hl=language
            ).execute()

            categories = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                categories.append({
                    'id': item.get('id', ''),
                    'title': snippet.get('title', ''),
                    'assignable': snippet.get('assignable', False),
                    'channel_id': snippet.get('channelId', ''),
                })

            return categories

        except Exception as e:
            raise RuntimeError(f"Failed to get video categories: {e}")

    def get_category_by_id(self, category_id: str,
                          language: str = 'en') -> Dict[str, Any]:
        """
        Get a specific video category by ID.

        Args:
            category_id: Video category ID
            language: Language for category name

        Returns:
            Category dictionary or None if not found
        """
        self._ensure_initialized()

        try:
            response = self._youtube.videoCategories().list(
                part='snippet',
                id=category_id,
                hl=language
            ).execute()

            if response.get('items'):
                item = response['items'][0]
                snippet = item.get('snippet', {})
                return {
                    'id': item.get('id', ''),
                    'title': snippet.get('title', ''),
                    'assignable': snippet.get('assignable', False),
                    'channel_id': snippet.get('channelId', ''),
                }
            return None

        except Exception as e:
            raise RuntimeError(f"Failed to get category by ID: {e}")

    # --- i18n Languages/Regions API ---

    def get_supported_languages(self, language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of languages supported by YouTube.

        Args:
            language: Language for displaying names (e.g., 'en', 'es')

        Returns:
            List of supported language dictionaries
        """
        self._ensure_initialized()

        try:
            response = self._youtube.i18nLanguages().list(
                part='snippet',
                hl=language
            ).execute()

            languages = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                languages.append({
                    'code': item.get('id', ''),  # Language code like 'en', 'es'
                    'name': snippet.get('name', ''),
                    'hl': snippet.get('hl', ''),
                })

            return languages

        except Exception as e:
            raise RuntimeError(f"Failed to get supported languages: {e}")

    def get_supported_regions(self, language: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of regions/countries supported by YouTube.

        Args:
            language: Language for displaying names (e.g., 'en', 'es')

        Returns:
            List of supported region dictionaries
        """
        self._ensure_initialized()

        try:
            response = self._youtube.i18nRegions().list(
                part='snippet',
                hl=language
            ).execute()

            regions = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                regions.append({
                    'code': item.get('id', ''),  # Region code like 'US', 'GB'
                    'name': snippet.get('name', ''),
                    'gl': snippet.get('gl', ''),
                })

            return regions

        except Exception as e:
            raise RuntimeError(f"Failed to get supported regions: {e}")

    # --- Activities API ---

    def get_channel_activities(self, channel_id: str, max_results: int = 25,
                              published_after: str = None,
                              published_before: str = None,
                              region_code: str = None,
                              page_token: str = None) -> Dict[str, Any]:
        """
        Get activity feed for a channel.

        Activity types include: upload, like, favorite, comment, subscription,
        playlistItem, recommendation, bulletin, channelItem, social, etc.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of results (max 50)
            published_after: ISO 8601 datetime (e.g., '2024-01-01T00:00:00Z')
            published_before: ISO 8601 datetime
            region_code: Filter by region (e.g., 'US')
            page_token: Token for pagination

        Returns:
            Dictionary with activities and pagination info
        """
        self._ensure_initialized()

        try:
            params = {
                'part': 'snippet,contentDetails',
                'channelId': channel_id,
                'maxResults': min(max_results, 50),
            }

            if published_after:
                params['publishedAfter'] = published_after
            if published_before:
                params['publishedBefore'] = published_before
            if region_code:
                params['regionCode'] = region_code
            if page_token:
                params['pageToken'] = page_token

            response = self._youtube.activities().list(**params).execute()

            activities = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                content_details = item.get('contentDetails', {})

                # Determine activity type and extract relevant content
                activity_type = snippet.get('type', 'unknown')
                content = content_details.get(activity_type, {})

                activities.append({
                    'activity_id': item.get('id', ''),
                    'type': activity_type,
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'channel_id': snippet.get('channelId', ''),
                    'channel_title': snippet.get('channelTitle', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                    'content': content,
                    'group_id': snippet.get('groupId', ''),
                })

            return {
                'activities': activities,
                'total_results': response.get('pageInfo', {}).get('totalResults', len(activities)),
                'next_page_token': response.get('nextPageToken'),
                'prev_page_token': response.get('prevPageToken'),
                'quota_cost': 1,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to get channel activities: {e}")

    def get_recent_uploads(self, channel_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent video uploads from a channel's activity feed.

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of uploads to return

        Returns:
            List of recent upload dictionaries
        """
        self._ensure_initialized()

        try:
            result = self.get_channel_activities(channel_id, max_results=50)

            uploads = []
            for activity in result.get('activities', []):
                if activity['type'] == 'upload':
                    content = activity.get('content', {})
                    uploads.append({
                        'video_id': content.get('videoId', ''),
                        'title': activity.get('title', ''),
                        'description': activity.get('description', ''),
                        'published_at': activity.get('published_at', ''),
                        'thumbnail': activity.get('thumbnail', ''),
                        'url': f"https://www.youtube.com/watch?v={content.get('videoId', '')}",
                    })

                    if len(uploads) >= max_results:
                        break

            return uploads

        except Exception as e:
            raise RuntimeError(f"Failed to get recent uploads: {e}")

    # --- Trending/Popular Videos API ---

    def get_trending_videos(self, region_code: str = 'US',
                           category_id: str = None,
                           max_results: int = 25,
                           page_token: str = None) -> Dict[str, Any]:
        """
        Get trending/most popular videos in a region.

        Args:
            region_code: ISO 3166-1 alpha-2 country code (e.g., 'US', 'GB', 'JP')
            category_id: Filter by video category ID (optional)
            max_results: Maximum number of results (max 50)
            page_token: Token for pagination

        Returns:
            Dictionary with trending videos and pagination info
        """
        self._ensure_initialized()

        try:
            params = {
                'part': 'snippet,contentDetails,statistics',
                'chart': 'mostPopular',
                'regionCode': region_code,
                'maxResults': min(max_results, 50),
            }

            if category_id:
                params['videoCategoryId'] = category_id
            if page_token:
                params['pageToken'] = page_token

            response = self._youtube.videos().list(**params).execute()

            videos = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                statistics = item.get('statistics', {})
                content_details = item.get('contentDetails', {})

                videos.append({
                    'video_id': item.get('id', ''),
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', '')[:200],
                    'channel_id': snippet.get('channelId', ''),
                    'channel_title': snippet.get('channelTitle', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                    'duration': content_details.get('duration', ''),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                    'category_id': snippet.get('categoryId', ''),
                    'tags': snippet.get('tags', []),
                    'url': f"https://www.youtube.com/watch?v={item.get('id', '')}",
                })

            return {
                'videos': videos,
                'region_code': region_code,
                'category_id': category_id,
                'total_results': response.get('pageInfo', {}).get('totalResults', len(videos)),
                'next_page_token': response.get('nextPageToken'),
                'prev_page_token': response.get('prevPageToken'),
                'quota_cost': 1,
            }

        except Exception as e:
            raise RuntimeError(f"Failed to get trending videos: {e}")

    def get_trending_by_category(self, region_code: str = 'US',
                                 language: str = 'en') -> Dict[str, List[Dict[str, Any]]]:
        """
        Get trending videos organized by category.

        Args:
            region_code: ISO 3166-1 alpha-2 country code
            language: Language for category names

        Returns:
            Dictionary mapping category names to lists of trending videos
        """
        self._ensure_initialized()

        try:
            # Get categories for the region
            categories = self.get_video_categories(region_code, language)

            trending_by_category = {}

            # Get trending for each assignable category
            for category in categories:
                if category['assignable']:
                    try:
                        result = self.get_trending_videos(
                            region_code=region_code,
                            category_id=category['id'],
                            max_results=10
                        )
                        if result['videos']:
                            trending_by_category[category['title']] = result['videos']
                    except:
                        continue  # Skip categories with no trending videos

            return trending_by_category

        except Exception as e:
            raise RuntimeError(f"Failed to get trending by category: {e}")

    # --- Channel Sections API ---

    def get_channel_sections(self, channel_id: str,
                            language: str = None) -> List[Dict[str, Any]]:
        """
        Get channel sections (shelves) that organize content on a channel page.

        Sections can include: uploads, playlists, featured channels, etc.

        Args:
            channel_id: YouTube channel ID
            language: Language for localized metadata

        Returns:
            List of channel section dictionaries
        """
        self._ensure_initialized()

        try:
            params = {
                'part': 'snippet,contentDetails',
                'channelId': channel_id,
            }

            if language:
                params['hl'] = language

            response = self._youtube.channelSections().list(**params).execute()

            sections = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                content_details = item.get('contentDetails', {})

                sections.append({
                    'section_id': item.get('id', ''),
                    'type': snippet.get('type', ''),
                    'title': snippet.get('title', ''),
                    'position': snippet.get('position', 0),
                    'default_language': snippet.get('defaultLanguage', ''),
                    'localized_title': snippet.get('localized', {}).get('title', ''),
                    'style': snippet.get('style', ''),
                    'playlists': content_details.get('playlists', []),
                    'channels': content_details.get('channels', []),
                })

            # Sort by position
            sections.sort(key=lambda x: x['position'])

            return sections

        except Exception as e:
            raise RuntimeError(f"Failed to get channel sections: {e}")

    def get_channel_featured_channels(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get featured channels from a channel's sections.

        Args:
            channel_id: YouTube channel ID

        Returns:
            List of featured channel IDs
        """
        self._ensure_initialized()

        try:
            sections = self.get_channel_sections(channel_id)

            featured_channels = []
            for section in sections:
                if section['type'] in ['multiplePlaylists', 'multipleChannels', 'singlePlaylist']:
                    featured_channels.extend(section.get('channels', []))

            return list(set(featured_channels))  # Remove duplicates

        except Exception as e:
            raise RuntimeError(f"Failed to get featured channels: {e}")

    # --- Enhanced Channel Info ---

    def get_channel_info(self, channel_id: str = None,
                        username: str = None,
                        handle: str = None) -> Dict[str, Any]:
        """
        Get comprehensive channel information.

        Provide ONE of: channel_id, username, or handle.

        Args:
            channel_id: YouTube channel ID (e.g., 'UC...')
            username: Legacy YouTube username
            handle: YouTube handle (e.g., '@MrBeast')

        Returns:
            Dictionary with comprehensive channel info
        """
        self._ensure_initialized()

        try:
            params = {
                'part': 'snippet,contentDetails,statistics,brandingSettings,topicDetails,status',
            }

            if channel_id:
                params['id'] = channel_id
            elif username:
                params['forUsername'] = username
            elif handle:
                # Handle needs to be searched
                params['forHandle'] = handle
            else:
                raise ValueError("Provide one of: channel_id, username, or handle")

            response = self._youtube.channels().list(**params).execute()

            if not response.get('items'):
                return None

            item = response['items'][0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            branding = item.get('brandingSettings', {})
            topic_details = item.get('topicDetails', {})
            status = item.get('status', {})

            return {
                'channel_id': item.get('id', ''),
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'custom_url': snippet.get('customUrl', ''),
                'published_at': snippet.get('publishedAt', ''),
                'country': snippet.get('country', ''),
                'default_language': snippet.get('defaultLanguage', ''),

                # Thumbnails
                'thumbnail_default': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                'thumbnail_medium': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                'thumbnail_high': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),

                # Statistics
                'view_count': int(statistics.get('viewCount', 0)),
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'hidden_subscriber_count': statistics.get('hiddenSubscriberCount', False),
                'video_count': int(statistics.get('videoCount', 0)),

                # Content details
                'uploads_playlist': content_details.get('relatedPlaylists', {}).get('uploads', ''),
                'likes_playlist': content_details.get('relatedPlaylists', {}).get('likes', ''),
                'favorites_playlist': content_details.get('relatedPlaylists', {}).get('favorites', ''),

                # Branding
                'keywords': branding.get('channel', {}).get('keywords', ''),
                'trailer_video_id': branding.get('channel', {}).get('unsubscribedTrailer', ''),
                'featured_channels_title': branding.get('channel', {}).get('featuredChannelsTitle', ''),
                'featured_channels_urls': branding.get('channel', {}).get('featuredChannelsUrls', []),
                'banner_url': branding.get('image', {}).get('bannerExternalUrl', ''),

                # Topics
                'topic_ids': topic_details.get('topicIds', []),
                'topic_categories': topic_details.get('topicCategories', []),

                # Status
                'privacy_status': status.get('privacyStatus', ''),
                'is_linked': status.get('isLinked', False),
                'long_uploads_status': status.get('longUploadsStatus', ''),
                'made_for_kids': status.get('madeForKids', False),
            }

        except Exception as e:
            raise RuntimeError(f"Failed to get channel info: {e}")

    def get_multiple_channels(self, channel_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get information for multiple channels at once.

        Args:
            channel_ids: List of YouTube channel IDs (max 50)

        Returns:
            List of channel info dictionaries
        """
        self._ensure_initialized()

        try:
            # Limit to 50 channels per request
            channel_ids = channel_ids[:50]

            response = self._youtube.channels().list(
                part='snippet,statistics',
                id=','.join(channel_ids)
            ).execute()

            channels = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                statistics = item.get('statistics', {})

                channels.append({
                    'channel_id': item.get('id', ''),
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', '')[:200],
                    'custom_url': snippet.get('customUrl', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                    'subscriber_count': int(statistics.get('subscriberCount', 0)),
                    'video_count': int(statistics.get('videoCount', 0)),
                    'view_count': int(statistics.get('viewCount', 0)),
                })

            return channels

        except Exception as e:
            raise RuntimeError(f"Failed to get multiple channels: {e}")
