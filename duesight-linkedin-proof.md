# DueSight buyer-demo proof note

## De korte versie

DueSight gebruikt een self-assessed historical replay om te laten zien hoe een
pre-DD signaal-laag werkt op publieke pre-event data. De replay is bedoeld voor
buyer-demo en pilotgesprekken, niet als publieke benchmark of certificering.

## Wat de replay laat zien

- Wirecard: reported-only financial math blijft NO-FLAG; de publieke
  pre-event signaal-laag flagt.
- Steinhoff: cutoff-fixed replay flagt op source-hard/proxy signalen; Viceroy is
  post-cutoff en telt niet mee.
- Imtech: v2-demo/source-limited; standalone public claim blijft geblokkeerd.
- Adler: eerlijke false negative pre-Viceroy.
- Deutsche Wohnen: negative-control case onder deze beperkte signaal-laag.

## Hoe het werkt

DueSight combineert bronvermelding, financial ratios, public-signal checks,
provider evidence en explicit limitations. Modeloutput telt nooit als bewijs
zonder bronpad, artifact of duidelijke blocked tier.

## Gebruik

Gebruik deze tekst alleen met de buyer-demo disclaimer: self-assessed,
reproduceerbaar, vaste cutoffs, beperkte sample, geen public leaderboard.

---

*Geplaatst door Arian | Founder DueSight*
