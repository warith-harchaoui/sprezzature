<!--
Linha de escrita, português (código de idioma: pt).
Fonte de verdade que a camada writing-standards lê em tempo de execução:
meta_from_ollama, plain_language, as legendas de lint_markdown e o ciclo Ralph
de prosa aplicam-na. Redigida de forma nativa em português, não traduzida.
Ver ../../references/writing-standards.md para saber como é aplicada.
-->

# Linha de escrita: português

Linha de escrita em português, válida para **qualquer texto**: artigo, capítulo,
nota, correio eletrónico, publicação, síntese de uma conversa com um modelo de
linguagem. Basta-se a si própria: o método de clareza e as regras de coerência
estão aqui integrados, não há outro ficheiro para abrir. Redigida de forma nativa
em português, não traduzida. Aplica-se conceito a conceito, linha a linha.

## 1. O princípio: torná-lo reconstruível

Compreender não é reter uma fórmula; é conseguir reconstruí-la e explicá-la a
alguém que nada sabe. Um texto conseguido faz mais do que informar: deixa o
leitor capaz de refazer o raciocínio sozinho.

O teste do principiante: se não se consegue explicar de forma simples, é porque
não se compreendeu. O sítio onde nos refugiamos atrás de uma palavra erudita é um
buraco na compreensão, não uma elegância; o jargão não é um atalho, é um
esconderijo. Quando uma frase não corre sem um termo por explicar, volta-se à
fonte até que corra.

## 2. O que vale a pena escrever: originalidade e importância

Antes de saber dizer bem, há que saber se o assunto vale a pena. Duas perguntas,
colocadas em conjunto:

- **Originalidade.** O assunto já existe tal e qual na literatura corrente, ou
  formula-se de uma maneira sem equivalente acessível? Um assunto inteiramente
  disponível noutro lado acrescenta pouco; um enquadramento, uma série reunida,
  uma reformulação que ilumina, acrescentam muito. Uma boa reformulação já é um
  trabalho original: o mérito reside muitas vezes no ângulo, não no facto nu.
- **Importância.** O que está em jogo é marginal (um parâmetro, um pormenor) ou
  estrutural (uma responsabilidade, uma soberania, uma saúde coletiva, uma
  economia)? Gasta-se o esforço de escrita onde o que está em jogo o justifica.

Guarda de honestidade: nunca apresentar como novo o que já existe. Antes de afirmar
uma novidade, verifica-se que não foi formulada noutro lado; na dúvida, assume-se o
papel do intérprete que dá a leitura clara, não o do inventor. Não se vende de mais.

## 3. O ciclo por conceito

Para cada noção (palavra técnica, sigla, fórmula, norma, nome próprio):
1. **Nomear** o conceito.
2. **Explicá-lo em linguagem simples**, como a um principiante, sem nenhum termo
   por definir.
3. **Encontrar o ponto de atrito**: a palavra ou o salto onde a explicação
   emperra. É aí que se esconde a obscuridade.
4. **Preencher e simplificar**: voltar à fonte, depois reformular com uma intuição
   em palavras e um exemplo concreto, até que o relato seja contínuo.

Um exemplo do gesto. *Antes*, partindo da fórmula: «Otimizamos um proxy sob
restrição de perímetro.» *Depois*, partindo da intuição: «Seguimos uma medida de
substituição, uma grandeza fácil de quantificar que vigiamos em vez do objetivo
real, que não sabemos medir diretamente; premiar cada erro corrigido, por exemplo,
acaba por incentivar a introdução de erros novos para os corrigir.» A segunda
versão nomeia o conceito, traduz-o em palavras, dá um caso concreto, assinala a
armadilha de passagem, sem um único termo deixado nu.

## 4. Lista de verificação por conceito

- **Intuição primeiro.** Uma imagem ou uma ideia em palavras precede qualquer
  fórmula ou abstração. A fórmula vem no fim, o resumo compacto de algo já
  compreendido, nunca o ponto de partida.
- **Um exemplo concreto.** Cada ideia recebe pelo menos um exemplo que um não
  especialista consiga imaginar (um objeto do quotidiano, um caso com números, uma
  cena).
- **Nenhum jargão nu.** Todo o termo técnico é explicado na primeira aparição; o
  leitor nunca precisa de um glossário para seguir o que lê.
- **Siglas.** Primeiro uma explicação em linguagem simples, depois o termo real,
  só então a abreviatura: «aprendizagem por reforço com humanos no ciclo
  (_reinforcement learning with human feedback_, ou RLHF)». Mantém-se o verdadeiro
  termo técnico em inglês; nunca se troca por uma paráfrase forçada que perca a sua
  precisão técnica.
- **Primeiros princípios.** O conceito deduz-se de uma base simples já assente, não
  de uma autoridade nem de outro termo obscuro.
- **Ancorar o novo no conhecido.** Toda a noção nova se prende a algo que o leitor
  já possui, em vez de flutuar sozinha.

## 5. As analogias (método A/B/C/D)

Uma analogia de relação transporta uma propriedade de um par conhecido para um par
a iluminar: o que A é para B, C é para D. Põe em jogo quatro termos; é a relação
entre A e B que se transfere para C e D. Antes de a usar, deve conseguir responder-se
a três perguntas: quais são os quatro termos? que propriedade se transporta do par
A e B para o par C e D? onde é que a semelhança deixa de valer?

Duas exigências opostas, sustentadas ao mesmo tempo:
1. **Nomear cedo, na prosa, os quatro termos e a propriedade transportada**, para
   que o leitor veja o que se coloca em confronto com o quê. Se não o vir, a
   analogia flutua e ele descarta-a.
2. **Nunca os expor como etiquetas.** Escrever «A está para B como C está para D»,
   alinhar letras ou uma proporção, torna o procedimento visível e mecânico; o
   leitor rejeita-o. A clareza vem da prosa, não do andaime.

Regra: **clara, mas nunca explícita.** O leitor deve conseguir refazer a semelhança
sozinho, sem que lhe tenham mostrado a estrutura A/B/C/D. E como toda a analogia
acaba por ceder, diz-se o ponto exato onde deixa de valer.

Exemplo. «Tal como um hospital, alimentado por uma rede elétrica fiável, mantém
ainda assim um gerador de emergência para não depender de uma única fonte, uma
organização que confia uma função vital a um serviço remoto precisa de um recurso
local.» Os quatro termos (rede e hospital de um lado, serviço remoto e organização
do outro) e a propriedade transportada (a necessidade de um apoio quando a
infraestrutura é vital) ficam límpidos, sem uma única letra nem proporção. E diz-se
onde quebra: o gerador arranca igual ao que substitui, ao passo que um recurso de
emergência em software fica muitas vezes degradado.

## 6. Coerência e honestidade

- **Não se inventa nada.** Clarifica-se e desenvolve-se o que está lá; nenhum facto
  não verificável acrescentado. Onde a compreensão para, di-lo.
- **Marcar o estatuto de prova.** Distingue-se sempre o que é *observado*,
  *medido*, *extrapolado* ou *especulativo*; uma afirmação empírica nunca aparece
  sem o seu grau de certeza.
- **Não imputar intenção sem o assinalar.** Não se atribui vontade nem agência a um
  sistema como se fosse um facto; se se usa um tal atalho, marca-se como tal.
- **O contraexemplo que ensina.** Uma regra compreende-se muitas vezes melhor no
  ponto onde quebra: um caso real que correu mal, com números e com fonte, ensina
  melhor do que o êxito. Duas condições para que sustente em vez de decorar: ilustra
  uma tese já enunciada, não a substitui; é solidificado como qualquer referência
  (números exatos, fonte primária, uma ligação que abre). Um contraexemplo vago
  vira-se contra o argumento.
- **Uma posição comedida.** Nem excesso num sentido nem no outro; não se cai no
  campo que simplifica. Os pensadores servem de leituras, não de adesões.
- **Um conceito, um lugar.** Uma noção define-se uma vez; noutro sítio remete-se
  para ela em vez de a redesenvolver. Nada contradiz em silêncio o que foi
  sustentado antes.

## 7. A forma

- **Nenhum travessão de pontuação.** Nada de travessão (o traço longo) nem de
  meia-risca (o traço médio) usados em incisa. O travessão é a norma para o
  diálogo, mas como recurso de aparte na prosa corrida fica banido aqui. Reescreve-se com vírgulas, dois pontos,
  ponto e vírgula, parênteses, frases curtas. Os hífenes das palavras compostas
  (sócio-técnico, tomada de decisão) ficam.
- **Aspas.** Preferem-se as aspas angulares «…» (norma europeia); as aspas curvas
  "…" são aceitáveis (uso comum no Brasil). Nada de espaços internos à francesa;
  nenhum espaço antes de `; : ? !`. As vírgulas e os pontos ficam colados à palavra.
- **Nenhum tique de máquina:** nada de «, e» nem de «, ou» a soldar duas orações
  (parte-se a frase, ou usa-se ponto e vírgula ou dois pontos), nada de «Por outras
  palavras», nada de ênfase por itálico à repetição, nenhuma tirada empolada.
- **Sem reflexo de antítese.** A construção «não é X, é Y», «não X mas Y» posta por
  automatismo assina o modelo. Guarda-se só quando a oposição é real e sustenta o
  argumento, nunca como efeito de gangorra.
- **Nenhuma frase-maratona.** Uma frase que passe da dezena de linhas no ecrã força
  um esforço de leitura desproporcionado, por mais correta que esteja. Corta-se em
  duas ou reestrutura-se. Desconfia-se também das listas disfarçadas, essas frases
  que enfiam uma enumeração sob uma sintaxe contínua: faz-se uma lista a sério ou
  frases separadas. O comprimento não prova a profundidade.
- **Nenhum tique lexical.** Um verbo ou uma construção que volta sempre («deslocar»,
  «ao mesmo tempo», «precisamente», «permite») trai o modelo. Localizam-se os ecos
  por pesquisa e variam-se, a não ser que a repetição seja um motivo deliberado.
- **Registo sóbrio, humano, elevado.** Nunca «à LLM», «à ChatGPT» nem «à Claude». A
  frase tem de soar à de um autor, não à de um modelo.
- **Caçar as marcas de ChatGPT.** Denunciam a máquina e desaparecem na releitura:
  - aberturas ocas: «Nos dias de hoje», «Na era de», «É importante notar que»,
    «Vale a pena salientar que», «Escusado será dizer que»;
  - transições aparafusadas em início de frase quando nenhum vínculo real as pede:
    «Além disso», «Por outro lado», «Ademais», «Em suma», «Por fim»;
  - tiques de reformulação: «Por outras palavras», «Em outras palavras», «Dito de
    outro modo», «Ou seja»;
  - intensificadores vazios postos para dar peso: «verdadeiramente»,
    «profundamente», «realmente», «literalmente», «fundamental», «crucial»,
    «essencial»;
  - gangorra reflexa: «não só X mas também Y», «não se trata apenas de X, mas de Y»;
  - fechos ocos: «Em conclusão», «Em resumo», «No fim de contas»;
  - abstrações inchadas: «o panorama de», «no cerne de», «um ponto de viragem» (no
    Brasil, «ponto de virada»), «navegar a complexidade de», «mergulhar em»;
  - simetria regular e ritmo ternário que alisam a prosa até ao anonimato.

  O remédio não é outra fórmula feita; é uma frase situada, de ritmo irregular, que
  diz a coisa e nada mais. A prosa de um autor tem arestas.

## 8. O idioma

O mais idiomático possível. Prefere-se sempre a construção que um falante culto
usaria à construção correta mas sem vida. Português direto e natural; nenhuma aspa
nem espaçamento à francesa transportados.

Pontuação portuguesa: aspas angulares «…», sem os espaços internos do francês, sem
espaço antes de `; : ? !`. Onde as convenções de Portugal e do Brasil divergem, o
texto lê-se com naturalidade para qualquer leitor, e assinalam-se aqui as
principais bifurcações: «por outras palavras» (Portugal) contra «em outras
palavras» (Brasil); «ponto de viragem» contra «ponto de virada»; «correio
eletrónico» contra «correio eletrônico»; «ficheiro» contra «arquivo»; a colocação
do pronome («explicá-lo» em Portugal soa mais natural que «lo explicar»). Escolhe-se
uma variante e mantém-se em todo o texto, sem misturar as duas na mesma página.

## 9. As fontes

Nenhuma referência gratuita. Uma citação diz o que a fonte estabelece, por que
método, com que limite, e por que é decisiva naquele ponto. Lê-se realmente a fonte
antes de a usar. Bane-se o «como tão bem diz X» e o name-dropping decorativo. Uma só
citação forte por afirmação.

A igual pertinência, equilibram-se as vozes: quando várias fontes têm igual
autoridade, citam-se de bom grado as autoras de referência onde existam. Nunca se
retira uma fonte por esta razão; é uma atenção ao equilíbrio, não uma quota.

## 10. O ciclo Ralph: fluidez por pares de parágrafos

Um texto relê-se não parágrafo a parágrafo, mas por pares de parágrafos
consecutivos, pois a fluidez joga-se na costura, não dentro de um bloco. O ciclo,
tomado do método «renderizar, olhar, corrigir o código, repetir»:

1. **Ler em voz alta** o parágrafo *n* seguido do parágrafo *n+1*, de um só fôlego.
2. **Olhar para a costura:** a passagem de um ao outro encadeia-se por si? O
   primeiro chama o segundo? Há uma repetição, um buraco lógico, um salto, uma
   palavra repetida de um bloco para o outro, uma transição aparafusada («além
   disso», «por outro lado») a tapar a falta de vínculo real?
3. **Corrigir a prosa, nunca a impressão:** mexe-se no texto em si (ordem das
   frases, última linha de *n*, primeira de *n+1*, uma retoma, um corte); não basta
   anotar que «isto range».
4. **Reler o par**, depois **avançar um passo:** desliza-se para o par (*n+1*,
   *n+2*) e recomeça-se. As janelas sobrepõem-se, de modo que cada parágrafo é
   posto à prova duas vezes, uma como chegada, outra como partida.

Fica-se num par até a costura desaparecer, depois passa-se ao seguinte. O texto flui
quando nenhuma junta se vê.

## 11. O gesto, numa imagem

A pedagogia do cozinheiro que **publica a receita** em vez do chef que guarda o
segredo: mostrar cada gesto, do primeiro princípio ao resultado, para que o leitor
refaça o prato sozinho. Uma passagem está pronta quando um leitor não especialista,
tendo-a lido uma vez, saberia reexplicá-la por sua vez.
