import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from PIL import Image, ImageFont

log: logging.Logger = logging.getLogger(__name__)


class Utility:
    """Utilitarian functions intended to reduce duplicate code."""

    def ReadFile(
        self: Any, path: str
    ) -> Optional[Union[Dict[str, Any], List[Any], str]]:
        """Read and return the contents of the specified file."""

        try:
            with open(path, "r") as file:
                if path.rsplit(".")[1] == "json":
                    return json.loads(file.read())
                else:
                    return file.read()
        except Exception as e:
            log.error(f"Failed to read file {path}, {e}")

    def WriteFile(
        self: Any, path: str, contents: Union[str, dict, list], **kwargs
    ) -> None:
        """Write the contents of the specified file."""

        try:
            with open(path, "w+") as file:
                if path.rsplit(".")[1] == "json":
                    if kwargs.get("compress") is True:
                        file.write(json.dumps(contents, ensure_ascii=False))
                    else:
                        file.write(json.dumps(contents, indent=4, ensure_ascii=False))
                else:
                    file.write(contents)
        except Exception as e:
            log.error(f"Failed to write file {path}, {e}")

    def FileExists(self: Any, path: str) -> bool:
        """
        Return a boolean value indicating whether or not the specified
        file exists.
        """

        if Path(path).is_file():
            return True

        return False

    def GetFileSize(self: Any, path: str) -> int:
        """Return the size (in bytes) of the specified file."""

        return Path(path).stat().st_size

    def OpenImage(
        self: Any, filename: str, directory: str = "assets/images/"
    ) -> Image.Image:
        """Return the image object for the specified file."""

        try:
            return Image.open(f"{directory}{filename}", "RGBA")
        except ValueError:
            return Image.open(f"{directory}{filename}").convert("RGBA")
        except Exception as e:
            log.error(f"Failed to read image file, {e}")

    def GET(self: Any, url: str) -> Optional[Union[Dict[str, Any], str]]:
        """
        Perform an HTTP GET request to the specified URL and return its
        response if the request is successful.
        """

        res: httpx.Response = httpx.get(url)

        # HTTP 200 OK
        if res.status_code == 200:
            contentType: Optional[str] = res.headers.get("content-type")

            if contentType == "application/json; charset=utf-8":
                return res.json()
            elif contentType == "application/json":
                return res.json()

            return res.text
        else:
            log.error(f"Failed to GET {url} (HTTP {res.status_code}):\n{res.text}")

    def POST(
        self: Any,
        url: str,
        headers: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Optional[Union[Dict[str, Any], str]]:
        """
        Perform an HTTP POST request to the specified URL with optional
        headers and content and return its response if the request is
        successful.
        """

        res: httpx.Response = httpx.post(
            url, headers=headers, json=data, files=files, timeout=30.0
        )
        status: int = res.status_code

        # HTTP 200 OK or HTTP 204 No Content
        if (status == 200) or (status == 204):
            contentType: Optional[str] = res.headers.get("content-type")

            if contentType == "application/json; charset=utf-8":
                return res.json()
            elif contentType == "application/json":
                return res.json()

            return res.text
        else:
            log.error(f"Failed to POST {url} (HTTP {status}):\n{res.text}")

    def DownloadImage(self: Any, url: str) -> Image.Image:
        """Download the specified image file and return the image object."""

        with httpx.stream("GET", url, timeout=30.0) as res:
            if res.status_code == 200:
                try:
                    return Image.open(res, "RGBA")
                except ValueError:
                    return Image.open(res).convert("RGBA")
            else:
                log.error(f"Failed to download image (HTTP {res.status_code})")

    def UploadImage(self: Any, path: str, token: str) -> Optional[str]:
        """Upload the specified image to the Hep.GG service and return its URL."""

        with open(path, "rb") as file:
            res: Dict[str, Any] = Utility.POST(
                self,
                "https://hep.gg/upload",
                headers={"Authorization": token},
                files={"upload-file": file},
            )

        return res.get("url")

    def ISOtoHuman(self: Any, date: str) -> str:
        """Return the provided ISO8601 timestamp in human-readable format."""

        date: str = date.split("T")[0]

        try:
            # Unix-supported zero padding removal
            return datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %-d, %Y")
        except ValueError:
            try:
                # Windows-supported zero padding removal
                return datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %#d, %Y")
            except Exception as e:
                log.error(f"Failed to convert timestamp to human-readable format, {e}")

    def NowISO(self: Any) -> str:
        """Return the current UTC timestamp in ISO format."""

        return datetime.utcnow().isoformat()

    def ResizeImage(
        self: Any,
        image: Image.Image,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Image.Image:
        """
        Resize the provided image object, optionally maintaining a
        calculated aspect ratio.
        """

        if (width is not None) and (height is not None):
            return image.resize((width, height), Image.ANTIALIAS)
        elif (width is not None) and (height is None):
            if image.width > width:
                change: float = width / image.width
                height = int(image.height * change)
            elif image.width < width:
                change: float = width / image.width
                height = int(image.height * change)

            return image.resize((width, height), Image.ANTIALIAS)
        elif (width is None) and (height is not None):
            if image.height > height:
                change: float = height / image.height
                width = int(image.width * change)
            elif image.height < height:
                change: float = height / image.height
                width = int(image.width * change)

            return image.resize((width, height), Image.ANTIALIAS)

    def CompressImage(
        self: Any, inPath: str, outPath: str, outSize: int, percentage: float = 0.9
    ) -> None:
        """Resize an image at the specified rate until it is below the desired threshold."""

        inSize: int = Utility.GetFileSize(self, inPath)
        inImage: Image.Image = Utility.OpenImage(self, inPath, "")
        inWidth: int = int(inImage.width * percentage)

        while inSize > outSize:
            outImage: Image.Image = Utility.ResizeImage(self, inImage, width=inWidth)
            outImage.save(outPath)

            inSize = Utility.GetFileSize(self, outPath)
            inWidth = int(inWidth * percentage)

    def GetTTF(
        self: Any, size: int, name: str, directory: str = "assets/fonts/"
    ) -> ImageFont.truetype:
        """Get the font object for the specified TrueType Font file and size."""

        try:
            return ImageFont.truetype(f"{directory}{name}.ttf", size)
        except Exception as e:
            log.error(f"Failed to load TrueType Font, {e}")

    def CenterX(
        self: Any, foregroundWidth: int, backgroundWidth: int, marginTop: int = 0
    ) -> Tuple[int, int]:
        """
        Calculate the tuple necessary to center across the X-Axis,
        optionally specify a Y-Axis margin.
        """

        return (int(backgroundWidth / 2) - int(foregroundWidth / 2), marginTop)
