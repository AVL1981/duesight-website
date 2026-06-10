# DueSight - Self-Assessed Historical Replay

**Laatst bijgewerkt:** 2026-06-03
**Status:** buyer-demo baseline, source-limited

Deze pagina vervangt de oude high-water scorepagina. Gebruik de resultaten alleen
als self-assessed historical replay op pre-event publieke signalen, niet als
public benchmark, certificering of investeringsadvies.

## Canonieke samenvatting

In een self-assessed, reproduceerbare historical replay op pre-event publieke
signalen komen Wirecard en Steinhoff als source-hard/proxy hoog-risico naar
voren; Imtech blijft v2-demo/source-limited; Adler pre-Viceroy is een false
negative; en Deutsche Wohnen blijft NO-FLAG onder deze beperkte test/source set.
De math-bonnen en limitations zitten erbij.

## Resultaten per laag

| Case | Signaal-laag | Source-hard overlay | Buyer-safe interpretatie |
|---|---:|---:|---|
| Wirecard AG | FLAG 7/10 | FLAG 5/>=3 | Reported-only math mist Wirecard; publieke pre-event signalen flaggen, met regulator count en adverse-media count geblokkeerd of retry-only. |
| Steinhoff International Holdings N.V. | FLAG 3/10 | FLAG 3/>=3 | Cutoff-fixed replay; Viceroy blijft post-cutoff context en telt niet mee. |
| Imtech N.V. | FLAG 3/10 | NO-FLAG 1/>=3 | Alleen v2-demo/source-limited; standalone claim-safe FLAG blijft geblokkeerd tot annual-report input extraction en short-seller artifacts source-hard zijn. |
| Adler Group S.A. | NO-FLAG 1/10 | not run | Eerlijke false negative pre-Viceroy; het Viceroy report valt na de cutoff. |
| Deutsche Wohnen SE | NO-FLAG 1/10 | not run | Negative-control case onder deze beperkte signaal-laag en source set. |

## Wat dit wel en niet bewijst

- Wel: DueSight kan een reproduceerbare pre-DD buyer-demo tonen met vaste cutoffs,
  deterministische math-bonnen en expliciete limitations.
- Niet: geen statistische validatieclaim, geen markt-exclusiviteitsclaim, geen
  certificering en geen investment recommendation.
- Open: grotere holdout, externe review en verdere source-hardening blijven nodig
  voordat publieke performanceclaims worden gemaakt.

## Verificatie

De buyer-demo baseline hoort alleen gebruikt te worden nadat de lokale
backtest-claim gate PASS geeft en de actuele buyer-pack limitations zijn gelezen.
