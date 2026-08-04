import json
import urllib.parse
import requests


class YoutubeSearch:
    def __init__(self, search_terms: str, max_results=None, proxy={}, retries=3, timeout=10):
        self.search_terms = search_terms
        self.max_results = max_results
        self.proxy = proxy
        self.retries = retries
        self.timeout = timeout
        self.videos = self._search()

    def _search(self):
        encoded_search = urllib.parse.quote_plus(self.search_terms)
        BASE_URL = "https://youtube.com"
        url = f"{BASE_URL}/results?search_query={encoded_search}"

        attempts = 1
        response = requests.get(url, proxies=self.proxy, timeout=self.timeout).text

        while "ytInitialData" not in response and attempts <= self.retries:
            response = requests.get(url, proxies=self.proxy, timeout=self.timeout).text
            attempts += 1

        results = self._parse_html(response)
        if self.max_results is not None and len(results) > self.max_results:
            return results[: self.max_results]
        return results

    def _parse_html(self, response):
        results = []
        start = (
            response.index("ytInitialData")
            + len("ytInitialData")
            + 3
        )
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = json.loads(json_str)

        for contents in data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"]:
            for video in contents["itemSectionRenderer"]["contents"]:
                res = {}
                if "videoRenderer" in video.keys():
                    video_data = video.get("videoRenderer", {})
                    res["id"] = video_data.get("videoId", None)
                    res["thumbnails"] = [
                        thumb.get("url", None)
                        for thumb in video_data.get("thumbnail", {}).get("thumbnails", [{}])
                    ]
                    res["title"] = video_data.get("title", {}).get("runs", [[{}]])[0].get("text", None)
                    res["long_desc"] = video_data.get("descriptionSnippet", {}).get("runs", [{}])[0].get("text", None)

                    # --- Extract channel name and channel URL safely ---
                    channel_runs = (
                        video_data
                        .get("longBylineText", {})
                        .get("runs", [])
                    )
                    channel_data = channel_runs[0] if channel_runs else {}
                    res["channel"] = channel_data.get("text", "Unknown Channel")
                    channel_path = (
                        channel_data
                        .get("navigationEndpoint", {})
                        .get("commandMetadata", {})
                        .get("webCommandMetadata", {})
                        .get("url", "")
                    )
                    res["channel_url"] = (
                        urllib.parse.urljoin("https://www.youtube.com", channel_path)
                        if channel_path
                        else ""
                    )
                    # ---------------------------------------------------

                    res["duration"] = video_data.get("lengthText", {}).get("simpleText", 0)
                    res["views"] = video_data.get("viewCountText", {}).get("simpleText", 0)
                    res["publish_time"] = video_data.get("publishedTimeText", {}).get("simpleText", 0)
                    res["url_suffix"] = video_data.get("navigationEndpoint", {}).get("commandMetadata", {}).get("webCommandMetadata", {}).get("url", None)
                    results.append(res)

            if results:
                return results
        return results

    def to_dict(self, clear_cache=True):
        result = self.videos
        if clear_cache:
            self.videos = ""
        return result

    def to_json(self, clear_cache=True):
        result = json.dumps({"videos": self.videos})
        if clear_cache:
            self.videos = ""
        return result