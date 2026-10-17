# Stato del nuovo progetto

Aggiornato:17ottobre2026. Responsabile:Director.

## Attivo — OBS-002/R1 DELIVERED (in attesa di review Director), consegna c8ac744 non ACCEPTED
La popolazione/esiti OBS-002 esistono: Claude riporta4372prime origini +2210ripetizioni, input27ZIP2022-10…2024-12, nessun2025/2026 o download. Config b11bad4557… invariata; metodi/convenzioni a6f1743d. Review Director:15test Python e24UI storici passati,typecheck/build riusciti,lettura codice/report e immagine dell'esecutore. Nessun ricalcolo reale indipendente di popolazione/esiti.

Tre rilievi nel task corrente e report §10:
- knownAtT delle timeline conserva replacedBy/sameGroup del ritiro futuro pur azzerandone data/motivo (riprodotto su sintetico);
- lettore accetta esiti completi con componente mancante o classi in conflitto coi contatti (due test aggiuntivi falliscono);
- testo «quasi sempre entrambi» errato: sui4368completi,2430entrambi55,63%,1900uno43,50%,38nessuno0,87%; almeno uno99,13%.

R1 consegnato da Claude il 17 ottobre (commit `bc92a6d`, report §11): timeline proiettate causalmente con derivato `R1/examples.json` (20 campi futuri rimossi nei 10 casi, originale conservato); validatore OBS002_CASE coerente su esiti, contatti, flag e censura; descrizione corretta, con almeno un contatto al 99,1% ed entrambi al 55,6%. Popolazione, esiti, summary e pacchetti invariati. Prossimo passo: review Director e lettura congiunta. Ambito R1 era: correggere solo proiezione/derivato delle timeline, confine del nuovo lettore e descrizione aritmetica. Nessun nuovo calcolo reale di popolazione/esiti, soglie, profili o orizzonte. Sette scelte tecniche del report §7 accettate. Il40%di profondità>1 è effetto del disegno Director, non bug Claude e non autorizza esclusioni dopo gli esiti.

## Obiettivo e prosecuzione
Una sola analisi esplorativa di movimento–arretramento–ripresa sul DEV già esposto, sei famiglie lette congiuntamente. Dopo R1 il Director completa la review e conclude con al massimo una ipotesi decisionale motivata/controesempi/verifica necessaria, oppure nessuna distinzione interpretabile e limite preciso. Nessuna ipotesi implementata o v2 automatica. Macrofase aperta; ad Astra alla conclusione o conflitto sostanziale, non per questi fix ordinari.

## Conservato e confini
CAND-001/D1 chiuso senza v2, accettato da Astra; famiglia non esclusa, una caratteristica non si scarta perché compare anche nei casi contrari. V1 negativa e non promossa. APP-001 concluso con riscontro positivo di Gian.
Solo file locali autorizzati,2025escluso,2026protetto,vecchi studiINACTIVE; nessun exchange/conto/ordine o stackOwner. Raw/outputestesi fuoriGit. Consultazione con storico esistente, nessun nuovo esploratore o cantiereUI. Nessuna suite generale o CI. Commit/push pertinenti autorizzati, checkout a curaGian.
