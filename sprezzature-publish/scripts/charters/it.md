<!--
Linea guida di scrittura — italiano (codice lingua: it).
Fonte di verità che il livello writing-standards legge in fase di esecuzione:
meta_from_ollama, plain_language, le didascalie di lint_markdown e il ciclo
Ralph di prosa la applicano. Redatta in modo nativo in italiano, non tradotta.
Vedere ../../references/writing-standards.md per come viene applicata.
-->

# Linea guida di scrittura — italiano

Linea guida per **qualsiasi testo** in italiano: articolo, capitolo, nota, email,
post, resoconto di una conversazione con un modello linguistico. Basta a se stessa:
il metodo di chiarezza e le regole di coerenza sono già dentro, non c'è nessun altro
file da aprire. La si applica concetto per concetto, riga per riga. Redatta in modo
nativo in italiano, non tradotta.

## 1. Il principio: renderlo ricostruibile

Capire non è ricordare una formula; è saperla ricostruire e spiegarla a chi non sa
nulla. Un testo riuscito non si limita a informare: lascia il lettore capace di
rifare il ragionamento da solo.

Il test del principiante: se non si sa spiegare in modo semplice, vuol dire che non
si è capito. Il punto in cui ci si rifugia dietro una parola dotta è un buco nella
comprensione, non un'eleganza; il gergo non è una scorciatoia, è un nascondiglio.
Quando una frase non scorre senza un termine non spiegato, si torna alla fonte finché
non scorre.

## 2. Cosa vale la pena scrivere: originalità e importanza

Prima di sapere come dirlo bene, bisogna sapere se il punto vale la pena. Due domande,
tenute insieme:

- **Originalità.** Il punto esiste già così com'è nella letteratura corrente, oppure lo
  si formula in un modo che non ha equivalenti a portata di mano? Un punto interamente
  reperibile altrove aggiunge poco; un'inquadratura, una serie messa insieme, una
  riformulazione che illumina, aggiungono molto. Una buona riformulazione è già di per
  sé un lavoro originale: il merito sta spesso nell'angolo, non nel fatto nudo.
- **Importanza.** La posta in gioco è marginale (una regolazione, un dettaglio) o
  strutturale (una responsabilità, una sovranità, una salute collettiva, un'economia)?
  Si spende lo sforzo di scrittura dove la posta lo giustifica.

Cautela di onestà: non presentare mai come nuovo ciò che esiste già. Prima di dichiarare
una novità, si verifica che non sia stata formulata altrove; nel dubbio, ci si pone come
interprete che dà la lettura chiara, non come inventore. Non si vende nulla più di
quanto valga.

## 3. Il ciclo per concetto

Per ogni nozione (parola tecnica, sigla, formula, standard, nome proprio):
1. **Nominare** il concetto.
2. **Spiegarlo in lingua piana**, come a un principiante, senza alcun termine non
   definito.
3. **Individuare il punto di attrito**: la parola o il salto dove la spiegazione si
   inceppa. È lì che si annida l'oscurità.
4. **Colmare e poi semplificare**: tornare alla fonte, quindi riformulare con
   un'intuizione a parole e un esempio concreto, finché il racconto non è continuo.

Un esempio del gesto. *Prima*, partendo dalla formula: «Ottimizziamo un proxy sotto
vincolo di perimetro.» *Dopo*, partendo dall'intuizione: «Seguiamo una misura
sostitutiva, una grandezza facile da quantificare che teniamo d'occhio al posto
dell'obiettivo vero, che non sappiamo misurare direttamente; premiare ogni difetto
corretto, per esempio, finisce per incoraggiare a introdurne di nuovi da correggere.»
La seconda versione nomina il concetto, lo traduce in parole, ne dà un caso concreto,
segnala la trappola di passaggio, senza un solo termine lasciato nudo.

## 4. Checklist per concetto

- **L'intuizione per prima.** Un'immagine o un'idea a parole precede ogni formula o
  astrazione. La formula viene alla fine, riassunto compatto di qualcosa già capito, mai
  punto di partenza.
- **Un esempio concreto.** Ogni idea riceve almeno un esempio che un non addetto ai
  lavori riesce a raffigurarsi (un oggetto di tutti i giorni, un caso con i numeri, una
  scena).
- **Nessun gergo nudo.** Ogni termine tecnico è glossato alla prima comparsa; il lettore
  non ha mai bisogno di un glossario per seguire.
- **Sigle.** Prima una glossa in lingua piana, poi il termine reale, poi soltanto
  l'abbreviazione: «apprendimento per rinforzo con umani nel ciclo (_Reinforcement
  Learning with Human Feedback_ o RLHF)». Si tiene il vero termine tecnico inglese; non
  lo si sostituisce con una parafrasi italiana forzata che ne perda la precisione.
- **Primi principi.** Il concetto si ricava da una base semplice già posata, non da
  un'autorità o da un altro termine oscuro.
- **Ancorare il nuovo al noto.** Ogni nozione nuova si aggancia a qualcosa che il lettore
  già possiede, invece di fluttuare da sola.

## 5. Le analogie (metodo A/B/C/D)

Un'analogia di relazione trasporta una proprietà da una coppia nota a una da illuminare:
ciò che A è per B, C lo è per D. Mette in gioco quattro termini; è la relazione fra A e B
che si trasferisce a C e D. Prima di servirsene, si deve poter rispondere a tre domande:
quali sono i quattro termini? quale proprietà si trasporta da A-B verso C-D? dove
l'accostamento smette di reggere?

Due esigenze opposte, tenute insieme:
1. **Nominare presto, nella prosa, i quattro termini e la proprietà trasportata**, così
   che il lettore veda cosa si mette a confronto con cosa. Se non lo vede, l'analogia
   fluttua e lui la scarta.
2. **Non esporli mai come etichette.** Scrivere «A sta a B come C sta a D», allineare
   lettere o una proporzione, rende il procedimento visibile e meccanico; il lettore lo
   respinge. La chiarezza viene dalla prosa, non dall'impalcatura.

Regola: **chiara, mai esplicita.** Il lettore deve poter ricostruire l'accostamento da
solo, senza che gli si sia mostrata l'ossatura A/B/C/D. E poiché ogni analogia prima o
poi cede, si segnala il punto esatto in cui smette di portare.

Esempio. «Come un ospedale, alimentato da una rete elettrica affidabile, tiene comunque
un generatore di emergenza per non dipendere da una sola fonte, così un'organizzazione
che affida una funzione vitale a un servizio remoto ha bisogno di un ripiego locale.» I
quattro termini (rete e ospedale da un lato, servizio remoto e organizzazione
dall'altro) e la proprietà trasportata (il bisogno di una scorta quando l'infrastruttura
è vitale) sono limpidi, senza una sola lettera né proporzione. E si dice dove si rompe:
il generatore riparte identico, un ripiego software resta spesso degradato.

## 6. Coerenza e onestà

- **Non si inventa nulla.** Si chiarisce e si sviluppa ciò che c'è; nessun fatto non
  verificabile aggiunto. Dove la comprensione si ferma, lo si dice.
- **Marcare lo stato della prova.** Si distingue sempre ciò che è *osservato*, *misurato*,
  *estrapolato* o *speculativo*; un'affermazione empirica non compare mai senza il suo
  grado di certezza.
- **Non attribuire intenzioni senza segnalarlo.** Non si attribuisce né volontà né
  agentività a un dispositivo come se fosse un fatto; se si usa una tale scorciatoia, la
  si marca come tale.
- **Il controesempio che insegna.** Una regola si coglie spesso meglio nel punto in cui
  si rompe: un caso reale finito male, con i numeri e la fonte, insegna più di quello
  riuscito. Due condizioni perché porti invece di decorare: illustra una tesi già posta,
  non la sostituisce; è solidificato come qualsiasi riferimento (cifre esatte, fonte
  primaria, un link che risolve). Un controesempio approssimativo si ritorce contro
  l'argomento.
- **Una posizione misurata.** Nessun eccesso in un senso o nell'altro; non si scivola
  nel campo che semplifica. Gli autori si usano come letture, non come adesioni.
- **Un concetto, un posto.** Una nozione si definisce una volta; altrove vi si rimanda
  invece di risvilupparla. Nulla contraddice in silenzio ciò che si è tenuto prima.

## 7. La forma

- **Nessuna lineetta di punteggiatura.** Niente lineetta lunga (il segno «—») né lineetta
  media (il segno «–») usate come inciso. Si riscrive con virgole, due punti, punti e
  virgola, parentesi, frasi brevi. I trattini dei composti (socio-tecnico, tecnico-
  scientifico) restano.
- **Punteggiatura italiana, non francese.** Si preferiscono i caporali «…» (la norma
  italiana); le virgolette alte "…" sono ammesse. Nessuno spazio interno alla francese
  dentro i caporali; nessuno spazio prima di `; : ? !`; virgole e punti stanno attaccati
  alla parola. Elisioni e apostrofi corretti: «l'analogia», «un'immagine», «dell'errore».
- **Nessun tic di macchina:** niente «, e» né «, o» che saldano due proposizioni (si
  spezza la frase, oppure si mette un punto e virgola o un due punti); niente «In altre
  parole»; niente regola del tre sistematica; niente enfasi in corsivo a ripetizione;
  niente giro di parole gonfio.
- **Nessun riflesso di antitesi.** La formula «non è X, è Y», «non X ma Y» posata per
  automatismo firma il modello preconfezionato. La si tiene solo quando l'opposizione è
  reale e porta l'argomento, mai come effetto a bilanciere.
- **Nessuna frase-maratona.** Una frase che supera una decina di righe sullo schermo
  impone uno sforzo di lettura sproporzionato, per quanto grammaticalmente giusta. La si
  taglia in due o la si ristruttura. Attenzione anche alle liste travestite, quelle frasi
  che infilano un'enumerazione dentro una sintassi continua: se ne fa una vera lista o
  frasi distinte. La lunghezza non è profondità.
- **Nessun tic lessicale.** Uno stesso verbo o una stessa formula che torna («spostare»,
  «al contempo», «per l'appunto», «consente di») tradisce il modello. Si stanano gli echi
  con una ricerca e si varia, salvo quando la ripresa è un motivo voluto.
- **Registro sobrio, umano, elevato.** Mai «da LLM», «da ChatGPT» né «da Claude». La frase
  deve suonare come quella di un autore, non di un modello preconfezionato.
- **Stanare le firme da ChatGPT.** Tradiscono la macchina e svaniscono alla rilettura:
  - aperture vuote: «Al giorno d'oggi», «Nell'era di», «È importante notare che», «Vale
    la pena sottolineare che», «Non è un segreto che»;
  - transizioni incollate in testa alla frase quando nessun legame reale le chiama:
    «Inoltre», «Peraltro», «D'altra parte», «In definitiva», «In fin dei conti»;
  - riformulazione-tic: «In altre parole», «Detto altrimenti», «Per dirla in altro modo»;
  - intensificatori vuoti posati per dare peso: «davvero», «profondamente», «veramente»,
    «fondamentale», «cruciale», «essenziale», «letteralmente»;
  - bilanciere per riflesso: «non solo X ma anche Y», «non si tratta soltanto di X, ma
    anche di Y»;
  - chiuse vuote: «In conclusione», «In sintesi», «Tutto sommato», «In ultima analisi»;
  - astrazioni gonfiate: «il panorama di», «nel cuore di», «un punto di svolta»,
    «navigare la complessità di», «immergersi in», «nell'ottica di»;
  - simmetria regolare e ritmo ternario che levigano la prosa fino all'anonimato.

  Il rimedio non è un'altra formula bell'e pronta; è una frase situata, dal ritmo
  irregolare, che dice la cosa e nulla di più. La prosa di un autore ha delle asperità.

## 8. L'idioma

Il più idiomatico possibile. Si preferisce sempre il giro di frase che userebbe un
italiano colto a quello corretto ma piatto. Italiano diretto e naturale; nessuna
abitudine francese trapiantata. Caporali «…» secondo la norma italiana, nessuno spazio
insécable alla francese prima di `; : ? !`, elisioni e apostrofi fatti come si deve
(«un'idea» con l'apostrofo al femminile, «un idea» senza al maschile è un errore da
evitare al contrario). Le d eufoniche solo davanti a vocale uguale («ad avere», «ed
ecco»), non a caso.

## 9. Le fonti

Nessun riferimento gratuito. Una citazione dice cosa la fonte stabilisce, con quale
metodo, con quale limite, e perché è decisiva in quel punto. Si legge davvero la fonte
prima di servirsene. Si bandiscono il «come dice benissimo X» e il name-dropping
decorativo. Una sola citazione forte per affermazione.

A pari rilevanza, si equilibrano le voci: quando più fonti hanno pari autorità, si
citano volentieri le autrici di riferimento dove esistono. Non si toglie mai una fonte
per questo motivo; è un'attenzione all'equilibrio, non una quota.

## 10. Il ciclo Ralph: scorrevolezza per coppie di paragrafi

Un testo si rilegge non paragrafo per paragrafo ma per coppie di paragrafi consecutivi,
perché la scorrevolezza si gioca alla cucitura, non dentro un blocco. Il ciclo, preso in
prestito dal metodo «rendi, guarda, correggi il codice, ripeti»:

1. **Leggere ad alta voce** il paragrafo *n* seguito dal paragrafo *n+1*, in un fiato.
2. **Guardare la cucitura**: il passaggio dall'uno all'altro si concatena da solo? Il
   primo chiama il secondo? C'è una ripetizione, un buco logico, un salto, una parola
   ripetuta da un blocco all'altro, una transizione incollata («inoltre», «peraltro»)
   che copre l'assenza di un legame reale?
3. **Correggere la prosa, mai l'impressione**: si ritocca il testo stesso (ordine delle
   frasi, ultima riga di *n*, prima di *n+1*, un richiamo, un taglio); non ci si limita a
   notare che «qui si inceppa».
4. **Rileggere la coppia**, poi **avanzare di un passo**: si scivola alla coppia (*n+1*,
   *n+2*) e si ricomincia. Le finestre si sovrappongono, così ogni paragrafo è messo alla
   prova due volte, una come arrivo, una come partenza.

Si gira su una coppia finché la cucitura non sparisce, poi si passa alla successiva. Il
testo scorre quando nessuna giuntura si vede più.

## 11. Il gesto, in un'immagine

La pedagogia del cuoco che **pubblica la ricetta** invece dello chef che custodisce il
segreto: mostrare ogni gesto, dal primo principio al risultato, perché il lettore rifaccia
il piatto da solo. Un passaggio è pronto quando un lettore non specialista, dopo averlo
letto una volta, saprebbe rispiegarlo a sua volta.
