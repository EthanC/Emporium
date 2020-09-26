import logging
from math import ceil
from sys import exit
from typing import Any, Dict, List, Optional, Tuple, Union

import coloredlogs
import praw
import twitter
from PIL import Image, ImageDraw

from utility import Utility

log: logging.Logger = logging.getLogger(__name__)
coloredlogs.install(level="INFO", fmt="[%(asctime)s] %(message)s", datefmt="%I:%M:%S")


class Emporium:
    """Call of Duty: Modern Warfare and Warzone Store generator."""

    def Initialize(self: Any) -> None:
        """Configure the application and begin its main functionality."""

        print("Emporium: Modern Warfare and Warzone Store Generator")
        print("https://github.com/EthanC/Emporium\n")

        if (config := Emporium.LoadConfiguration(self)) is None:
            return

        self.config: Dict[str, Any] = config

        if (store := Emporium.GetStore(self)) is None:
            return

        store: Dict[str, Any] = store

        if Emporium.DiffStore(self, store) is False:
            return

        store = Emporium.ProcessStore(self, store)

        if store is None:
            return

        image: bool = Emporium.BuildImage(self, store)

        if image is not True:
            return

        if self.config["thirdParties"]["twitter"].get("enabled") is True:
            Emporium.ShareTwitter(self, store)

        if self.config["thirdParties"]["discord"].get("enabled") is True:
            Emporium.ShareDiscord(self, store)

        if self.config["thirdParties"]["reddit"].get("enabled") is True:
            Emporium.ShareReddit(self, store)

        Utility.WriteFile(self, "latest.txt", store.get("hash"))

        log.info("Saved the latest Store hash")

    def LoadConfiguration(self: Any) -> Optional[Dict[str, Any]]:
        """Load the configurable values from config.json"""

        config: Optional[Dict[str, Any]] = Utility.ReadFile(self, "config.json")

        if config is not None:
            log.info("Loaded configuration")

            return config

    def GetStore(self: Any) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest Store data for Modern Warfare and Warzone from
        the Tracker Network API.
        """

        data: Optional[Any] = Utility.GET(
            self, "https://api.tracker.gg/api/v1/modern-warfare/store"
        )

        if data is None:
            return None

        store: Dict[str, Any] = data.get("data")
        updateDate: str = Utility.ISOtoHumanDate(self, store.get("lastUpdated"))
        updateTime: str = Utility.ISOtoHumanTime(self, store.get("lastUpdated"))

        log.info(f"Fetched the Store for {updateDate} at {updateTime} UTC")

        return store

    def DiffStore(self: Any, store: Dict[str, Any]) -> bool:
        """
        Determine if the Modern Warfare and Warzone Store has updated
        since the last time the application was ran.
        """

        apiHash: str = store.get("hash")

        if Utility.FileExists(self, "latest.txt") is False:
            Utility.WriteFile(self, "latest.txt", apiHash)

            log.warning("No local Store hash found, created it")

            return False

        localHash: str = Utility.ReadFile(self, "latest.txt")

        if localHash == apiHash:
            log.info("The Store has not updated, the local hash matches the API hash")

            return False
        else:
            return True

    def ProcessStore(self: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and return the Store API response."""

        featured: List[Dict[str, Any]] = []
        operators: List[Dict[str, Any]] = []
        blueprints: List[Dict[str, Any]] = []

        for bundle in data.get("items"):
            typeKey: str = bundle.get("typeKey")

            if typeKey == "FEATURED":
                featured.append(bundle)
            elif typeKey == "OPERATOR":
                operators.append(bundle)
            elif typeKey == "WEAPON":
                blueprints.append(bundle)
            else:
                log.warning(f"Unknown Bundle typeKey found: {typeKey}")

        lenF: int = len(featured)
        lenO: int = len(operators)
        lenB: int = len(blueprints)

        if (lenF == 0) or (lenO == 0) or (lenB == 0):
            if self.config["preferences"].get("verify") is True:
                log.error(
                    f"Failed to process the Store (Featured: {lenF:,}, Operators: {lenO:,}, Blueprints: {lenB:,})"
                )

                return None

        return {
            "updateDate": Utility.ISOtoHumanDate(self, data.get("lastUpdated")),
            "updateTime": Utility.ISOtoHumanTime(self, data.get("lastUpdated")),
            "hash": data.get("hash"),
            "featured": featured,
            "operators": operators,
            "blueprints": blueprints,
        }

    def BuildImage(self: Any, data: Dict[str, Any]) -> bool:
        """Generate a stylized image for the provided Store data."""

        background: Tuple[int, int, int] = tuple(
            self.config["appearance"].get("background")
        )
        text: Tuple[int, int, int] = tuple(self.config["appearance"].get("text"))

        fontName: str = self.config["appearance"].get("font")
        font72 = Utility.GetTTF(self, 72, fontName)
        font32 = Utility.GetTTF(self, 32, fontName)

        featured: List[Dict[str, Any]] = data.get("featured")
        operators: List[Dict[str, Any]] = data.get("operators")
        blueprints: List[Dict[str, Any]] = data.get("blueprints")

        dimensions: Tuple[int, int] = Emporium.CalculateDimensions(
            self, featured, operators, blueprints
        )

        store: Image = Image.new("RGBA", (dimensions[0], dimensions[1]))
        canvas: Any = ImageDraw.Draw(store)

        store.paste(background, (0, 0, store.width, store.height))

        gameLogo: Image.Image = Utility.OpenImage(self, "game_logo.png")
        gameLogo = Utility.ResizeImage(self, gameLogo, width=1000)
        store.paste(
            gameLogo, Utility.CenterX(self, gameLogo.width, store.width, 50), gameLogo
        )

        prettyDate: str = data.get("updateDate")
        textWidth, _ = font72.getsize(prettyDate)
        canvas.text(
            Utility.CenterX(self, textWidth, store.width, 275), prettyDate, text, font72
        )

        sectionX: int = 0
        sectionY: int = 500
        cardY: int = 0
        cardX: int = 0

        if len(featured) > 0:
            canvas.text((50, sectionY), "Featured", text, font72)

            i: int = 0

            for bundle in featured:
                card: Image.Image = Emporium.BuildCard(self, bundle, font32)

                cardX: int = sectionX + (50 + ((i % 2) * (card.width + 50)))
                cardY: int = 500 + (75 + 50) + (i // 2) * (card.height + 50)
                store.paste(card, (cardX, cardY), card)

                i += 1

            sectionX += 50 + (1005 * 2) + 50

        if len(operators) > 0:
            canvas.text((50 + sectionX, sectionY), "Operators & Identity", text, font72)

            i: int = 0

            for bundle in operators:
                card: Image.Image = Emporium.BuildCard(self, bundle, font32)

                cardX: int = sectionX + (50 + ((i % 2) * (card.width + 50)))
                cardY: int = 500 + (75 + 50) + (i // 2) * (card.height + 50)
                store.paste(card, (cardX, cardY), card)

                i += 1

            sectionX += 50 + (1005 * 2) + 50

        if len(blueprints) > 0:
            canvas.text((50 + sectionX, sectionY), "Blueprints", text, font72)

            i: int = 0

            for bundle in blueprints:
                card: Image.Image = Emporium.BuildCard(self, bundle, font32)

                cardX: int = sectionX + (50 + ((i % 2) * (card.width + 50)))
                cardY: int = 500 + (75 + 50) + (i // 2) * (card.height + 50)
                store.paste(card, (cardX, cardY), card)

                i += 1

            sectionX += 50 + (1005 * 2) + 50

        store.save("store.png", optimize=True)

        log.info("Generated the Store image")

        return True

    def CalculateDimensions(
        self: Any,
        featured: List[Dict[str, Any]],
        operators: List[Dict[str, Any]],
        blueprints: List[Dict[str, Any]],
    ) -> Tuple[int, int]:
        """Determine the dimensions needed for the image based on the Store data."""

        x: int = 0
        y: int = 500

        if len(featured) > 0:
            x += 50 + (1005 * 2) + 50

        if len(operators) > 0:
            x += 50 + (1005 * 2) + 50

        if len(blueprints) > 0:
            x += 50 + (1005 * 2) + 50

        x += 50
        y += (
            75
            + (
                (460 + 50)
                * ceil(max(len(featured), len(operators), len(blueprints)) / 2)
            )
        ) + 50

        return (x, y)

    def BuildCard(self: Any, bundle: Dict[str, Any], font: Any) -> Image.Image:
        """Generate a stylized image for the specified Bundle."""

        imageBaseUrl: str = "https://titles.trackercdn.com/modern-warfare/db/images/"

        card: Image.Image = Utility.OpenImage(self, "card_container.png")

        billboardUrl: str = imageBaseUrl + bundle.get("billboard") + ".png"
        billboard: Image.Image = Utility.DownloadImage(self, billboardUrl)
        billboard = Utility.ResizeImage(self, billboard, height=card.height)
        billboard = billboard.crop((258, 0, 1263, card.height))

        gradient: Image.Image = Utility.OpenImage(self, "card_gradient.png")
        billboard.alpha_composite(gradient)

        card.paste(billboard, Utility.CenterX(self, billboard.width, card.width), card)

        logoUrl: str = imageBaseUrl + bundle.get("logo") + ".png"
        logo: Image.Image = Utility.DownloadImage(self, logoUrl)
        logo = Utility.ResizeImage(self, logo, width=360)
        card.alpha_composite(logo, (25, 25))

        border: Image.Image = Utility.OpenImage(self, "card_border.png")
        card.alpha_composite(border)

        tag: Image.Image = Utility.OpenImage(self, "price_container.png")
        canvas: Any = ImageDraw.Draw(tag)
        price: Union[int, str] = bundle.get("price")
        canvas.text((50, 5), f"{price:,}", (255, 255, 255), font)
        card.alpha_composite(tag, (25, (card.height - tag.height - 25)))

        return card

    def ShareTwitter(self: Any, store: Dict[str, Any]) -> None:
        """Share the latest Store to the configured Twitter account."""

        updateDate: str = store.get("updateDate")
        updateTime: str = store.get("updateTime")
        creatorCode: str = self.config["preferences"].get("creatorCode")
        apiKey: str = self.config["thirdParties"]["twitter"].get("apiKey")
        apiSecret: str = self.config["thirdParties"]["twitter"].get("apiSecret")
        accessToken: str = self.config["thirdParties"]["twitter"].get("accessToken")
        accessSecret: str = self.config["thirdParties"]["twitter"].get("accessSecret")

        tweeter: twitter.Api = twitter.Api(
            consumer_key=apiKey,
            consumer_secret=apiSecret,
            access_token_key=accessToken,
            access_token_secret=accessSecret,
            timeout=30,
        )

        body: str = f"#ModernWarfare and #Warzone Store for {updateDate} at {updateTime} UTC\n\n"

        if creatorCode is not None:
            body += f"Consider supporting us! Use the Creator Code {creatorCode} in the Store to do so.\n\n"

        body += "Bundle Details: https://cod.tracker.gg/warzone/store"

        if Utility.GetFileSize(self, "store.png") >= 5242880:
            Utility.CompressImage(
                self, "store.png", "store_compressed.png", 5000000, 0.75
            )

            filename: str = "store_compressed"
        else:
            filename: str = "store"

        try:
            with open(f"{filename}.png", "rb") as file:
                tweeter.PostUpdate(body, media=file)
        except Exception as e:
            log.error(f"Failed to post to Twitter, {e}")

            return

        log.info("Shared the Store to Twitter")

    def ShareDiscord(self: Any, store: Dict[str, Any]) -> None:
        """Share the latest Store to the configured Discord webhooks."""

        updateDate: str = store.get("updateDate")
        updateTime: str = store.get("updateTime")
        creatorCode: str = self.config["preferences"].get("creatorCode")
        hepToken: str = self.config["thirdParties"]["discord"].get("hepToken")
        username: str = self.config["thirdParties"]["discord"].get("username")
        avatar: str = self.config["thirdParties"]["discord"].get("avatarUrl")
        webhooks: List[str] = self.config["thirdParties"]["discord"].get("webhookUrls")

        body: str = f"Modern Warfare and Warzone Store for {updateDate} at {updateTime} UTC\n\n"

        if creatorCode is not None:
            body += f"Consider supporting us! Use the Creator Code `{creatorCode}` in the Store to do so."

        body += "Bundle Details: [https://cod.tracker.gg/warzone/store](https://cod.tracker.gg/warzone/store)"

        imageURL: str = Utility.UploadImage(self, "store.png", hepToken)
        headers: Dict[str, Any] = {"content-type": "application/json"}
        embed: Dict[str, Any] = {
            "username": username,
            "avatar_url": avatar,
            "embeds": [
                {
                    "description": body,
                    "timestamp": Utility.NowISO(self),
                    "color": int("1DA1F2", base=16),
                    "footer": {
                        "text": "Twitter",
                        "icon_url": "https://i.hep.gg/6v2O1DLM3",
                    },
                    "image": {"url": imageURL},
                    "author": {
                        "name": "Call of Duty Tracker (@CODTracker)",
                        "url": "https://twitter.com/CODTracker",
                        "icon_url": "https://i.hep.gg/x1vphWfhx",
                    },
                }
            ],
        }

        count: int = 0

        for webhook in webhooks:
            Utility.POST(self, webhook, headers=headers, data=embed)

            count += 1

        log.info(f"Shared the Store to {count:,} Discord webhooks")

    def ShareReddit(self: Any, store: Dict[str, Any]) -> None:
        """Share the latest Store to the configured Reddit communities."""

        creatorCode: str = self.config["preferences"].get("creatorCode")
        username: str = self.config["thirdParties"]["reddit"].get("username")
        password: str = self.config["thirdParties"]["reddit"].get("password")
        clientId: str = self.config["thirdParties"]["reddit"].get("clientId")
        secret: str = self.config["thirdParties"]["reddit"].get("clientSecret")
        subreddits: List[str] = self.config["thirdParties"]["reddit"].get("communities")

        updateDate: str = store.get("updateDate")
        updateTime: str = store.get("updateTime")
        featured: List[Dict[str, Any]] = store.get("featured")
        operators: List[Dict[str, Any]] = store.get("operators")
        blueprints: List[Dict[str, Any]] = store.get("blueprints")

        reddit: praw.Reddit = praw.Reddit(
            username=username,
            password=password,
            client_id=clientId,
            client_secret=secret,
            user_agent="Emporium by /u/LackingAGoodName (https://github.com/EthanC/Emporium)",
        )
        reddit.validate_on_submit = True

        if reddit.read_only is not False:
            log.error("Failed to authenticate with Reddit")

            return

        count: int = 0

        for subreddit in subreddits:
            community: praw.reddit.Subreddit = reddit.subreddit(subreddit.get("name"))

            post: praw.reddit.Submission = community.submit_image(
                f"Modern Warfare and Warzone Store for {updateDate} at {updateTime} UTC",
                "store.png",
                subreddit.get("flairId"),
                subreddit.get("flairText"),
                send_replies=False,
                timeout=30,
                collection_id=subreddit.get("collectionId"),
            )

            if post is None:
                name: str = subreddit.get("name")
                log.error(f"Failed to submit to /r/{name}")

                continue

            body: str = ""

            if creatorCode is not None:
                body += f"Consider supporting us! Use the Creator Code `{creatorCode}` in the Store to do so.\n\n"

            if len(featured) > 0:
                body += "## Featured\n"

                for bundle in featured:
                    name: str = bundle.get("name")
                    url: str = "https://cod.tracker.gg/warzone/db/bundles/" + str(
                        bundle.get("id")
                    ) + "-" + bundle.get("slug")
                    price: int = bundle.get("price")

                    body += f"\n* [{name}]({url}) ({price:,} CODPoints)"

                body += "\n\n"

            if len(operators) > 0:
                body += "## Operators & Identity\n"

                for bundle in operators:
                    name: str = bundle.get("name")
                    url: str = "https://cod.tracker.gg/warzone/db/bundles/" + str(
                        bundle.get("id")
                    ) + "-" + bundle.get("slug")
                    price: int = bundle.get("price")

                    body += f"\n* [{name}]({url}) ({price:,} CODPoints)"

                body += "\n\n"

            if len(blueprints) > 0:
                body += "## Blueprints\n"

                for bundle in blueprints:
                    name: str = bundle.get("name")
                    url: str = "https://cod.tracker.gg/warzone/db/bundles/" + str(
                        bundle.get("id")
                    ) + "-" + bundle.get("slug")
                    price: int = bundle.get("price")

                    body += f"\n* [{name}]({url}) ({price:,} CODPoints)"

                body += "\n\n"

            comment: praw.reddit.Comment = post.reply(body)

            try:
                post.mod.approve()

                comment.mod.approve()
                comment.mod.distinguish(how="yes", sticky=True)
                comment.mod.lock()
            except Exception as e:
                log.warning(f"Failed to perform Moderator actions on Reddit, {e}")

            count += 1

        log.info(f"Shared the Store to {count:,} Reddit communities")


if __name__ == "__main__":
    try:
        Emporium.Initialize(Emporium)
    except KeyboardInterrupt:
        exit()
