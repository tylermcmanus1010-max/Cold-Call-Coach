# Brand Assets

Regenerate everything:

```
pip install pillow
python3 content-ops/assets/generate_brand.py --day 7 --calls 23
```

## Files

| File | Use |
|---|---|
| `avatar-1024.png` | Upload to all five platforms. Identical file everywhere. |
| `avatar-400.png` | Smaller copy for platforms that reject large uploads. |
| `avatar-legibility.png` | Proof sheet — the avatar circle-cropped at real display sizes. |
| `banner-x-1500x500.png` | X header. Lockup sits above centre so the profile pic doesn't cover it. |
| `banner-youtube-2560x1440.png` | YouTube. Content is inside the 1235×338 TV-safe area. |
| `banner-facebook-1640x664.png` | Facebook Page cover. |
| `scoreboard-dayNN.png` | The series end card. Regenerate daily. |

## Design decisions

- **Avatar is one shape.** A red record dot at 68% of the frame. The proof sheet
  is why: at 24–40px anything more than one shape turns to mud, and a smaller dot
  disappears entirely inside the circular crop every platform applies.
- **The black background merges with dark mode** on TikTok and Instagram, so the
  avatar reads as a floating red dot in-feed. That's intentional and it's the
  most distinctive thing about it.
- **Red, not blue.** Every B2B sales account uses corporate blue. Red reads as
  recording / on-air / alert — thematically correct and the only way to be
  visually distinct in the feed.
- **The scoreboard is the series' visual signature.** Same frame every day, only
  the number changes. Repetition is what makes it recognisable at a glance mid-scroll.
