# Emporium

Emporium is a utility which generates the current Store for Call of Duty: Modern Warfare and Warzone into a stylized image and shares it on Twitter, Discord, and Reddit.

Its data source is [COD Tracker](https://cod.tracker.gg/warzone/store), which is derived from Activision's [Call of Duty API](https://github.com/EthanC/CallofDuty.py).

<p align="center">
    <img src="https://i.imgur.com/mhvaMri.jpg" draggable="false">
</p>

## Requirements

-   [Python 3.8](https://www.python.org/downloads/)
-   [coloredlogs](https://pypi.org/project/coloredlogs/)
-   [HTTPX](https://www.python-httpx.org/)
-   [pillow](https://pillow.readthedocs.io/en/stable/installation.html)
-   [Python-Twitter](https://python-twitter.readthedocs.io/en/latest/installation.html)
-   [PRAW](https://praw.readthedocs.io/en/latest/getting_started/installation.html)

## Usage

Place your credentials and preferences in `config_example.json`, then save and rename the file to `config.json`. Then, simply run Emporium!

```
python emporium.py
```

## Thanks & Credits

-   [Activision](https://www.activision.com/) - Call of Duty Assets and API Service
