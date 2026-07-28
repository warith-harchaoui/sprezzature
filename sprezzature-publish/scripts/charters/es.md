<!--
Charter de escritura — español (código de idioma: es).
Fuente de verdad que la capa writing-standards lee en tiempo de ejecución:
meta_from_ollama, plain_language, los pies de figura de lint_markdown y el
bucle Ralph de prosa la aplican. Redactada de forma nativa en español, no
traducida. Véase ../../references/writing-standards.md para saber cómo se aplica.
-->

# Carta de estilo de escritura — español

Carta de estilo en español, válida para **cualquier texto**: artículo, capítulo,
nota, correo, entrada de blog, resumen de una conversación con un modelo de
lenguaje. Se basta a sí misma: el método de claridad y las reglas de coherencia
están integrados aquí, no hay otro archivo que abrir. Se aplica concepto a
concepto, línea a línea.

## 1. El principio: hacerlo reconstruible

Comprender no es retener una fórmula; es poder reconstruirla y explicársela a
alguien que no sabe nada. Un buen texto no se limita a informar: deja al lector
capaz de rehacer el razonamiento por su cuenta.

La prueba del principiante: si no sabes explicarlo con sencillez, es que no lo
has entendido. El lugar donde te escudas en una palabra culta es un hueco en la
comprensión, no una elegancia; la jerga no es un atajo, es un escondite. Cuando
una frase no fluye sin un término sin explicar, vuelve a la fuente hasta que
fluya.

## 2. Qué merece escribirse: originalidad e importancia

Antes de saber decirlo bien, hay que saber si el asunto merece decirse. Dos
preguntas, sostenidas a la vez:

- **Originalidad.** ¿Existe ya el asunto tal cual en la literatura corriente, o
  se formula de un modo que no tiene equivalente accesible? Un asunto del todo
  disponible en otra parte aporta poco; un encuadre, una serie reunida, una
  reformulación que ilumina, aportan mucho. Una buena reformulación ya es un
  trabajo original: el mérito suele estar en el ángulo, no en el hecho desnudo.
- **Importancia.** ¿El asunto en juego es marginal (un ajuste, un detalle) o
  estructural (una responsabilidad, una soberanía, una salud colectiva, una
  economía)? Gasta el esfuerzo de escritura donde el asunto lo justifique.

Salvaguarda de honestidad: nunca presentes como nuevo lo que ya existe. Antes de
afirmar una novedad, comprueba que no se ha dicho en otra parte; en la duda,
sitúate como el intérprete que da la lectura clara, no como el inventor. No
exageres nada.

## 3. El bucle por concepto

Para cada noción (palabra técnica, sigla, fórmula, norma, nombre propio):
1. **Nombra** el concepto.
2. **Explícalo en lenguaje llano**, como a quien empieza, sin ningún término
   sin definir.
3. **Localiza el punto de fricción**: la palabra o el salto donde la explicación
   se atasca. Ahí es donde se esconde la oscuridad.
4. **Rellena y luego simplifica**: vuelve a la fuente y reformula con una
   intuición en palabras y un ejemplo concreto, hasta que el relato no tenga
   cortes.

Un ejemplo del gesto. *Antes*, partiendo de la fórmula: «Optimizamos un proxy
sujeto a una restricción de perímetro.» *Después*, partiendo de la intuición:
«Seguimos una medida indirecta, una magnitud fácil de contar que vigilamos en
lugar del objetivo real, que no sabemos medir de forma directa; premiar cada
fallo corregido, por ejemplo, acaba animando a introducir fallos nuevos para
corregirlos.» La segunda versión nombra el concepto, lo traduce a palabras, da
un caso concreto y avisa de la trampa de pasada, sin dejar un solo término al
desnudo.

## 4. Lista de comprobación por concepto

- **La intuición primero.** Una imagen o una idea en palabras precede a
  cualquier fórmula o abstracción. La fórmula llega al final, resumen compacto
  de algo ya entendido, nunca punto de partida.
- **Un ejemplo concreto.** Cada idea recibe al menos un ejemplo que un
  no especialista pueda imaginar (un objeto cotidiano, un caso con cifras, una
  escena).
- **Nada de jerga desnuda.** Todo término técnico se glosa en su primera
  aparición; el lector nunca necesita un glosario para seguir lo que lee.
- **Siglas.** Primero una glosa llana en español, luego el término real en su
  forma original, y solo entonces la abreviatura: «aprendizaje por refuerzo con
  humanos en el bucle (_Reinforcement Learning with Human Feedback_, RLHF)». Se
  conserva el término de arte inglés real; no se sustituye por una paráfrasis
  forzada que perdería su precisión técnica.
- **Primeros principios.** El concepto se deduce de una base sencilla ya
  asentada, no de una autoridad ni de otro término oscuro.
- **Anclar lo nuevo en lo conocido.** Toda noción nueva se engancha a algo que
  el lector ya posee, en vez de flotar sola.

## 5. Las analogías (método A/B/C/D)

Una analogía de relación traslada una propiedad de una pareja conocida a otra que
hay que iluminar: lo que A es a B, C lo es a D. Pone en juego cuatro términos; es
la relación entre A y B la que se traslada a C y D. Antes de usarla, deberías
poder responder a tres preguntas: ¿cuáles son los cuatro términos?, ¿qué
propiedad se traslada de A y B a C y D?, ¿dónde deja de sostenerse el parecido?

Dos exigencias opuestas, sostenidas a la vez:
1. **Nombra pronto, en la prosa, los cuatro términos y la propiedad trasladada**,
   para que el lector vea qué se enfrenta a qué. Si no lo ve, la analogía flota y
   la descarta.
2. **No los expongas nunca como etiquetas.** Escribir «A es a B lo que C es a D»,
   alinear letras o una proporción, vuelve el recurso visible y mecánico; el
   lector lo rechaza. La claridad viene de la prosa, no del andamiaje.

Regla: **claro, nunca explícito.** El lector debe poder rehacer el parecido solo,
sin que le hayan mostrado el armazón A/B/C/D. Y como toda analogía acaba cediendo,
di el punto exacto donde deja de sostenerse.

Ejemplo. «Igual que un hospital, alimentado por una red eléctrica fiable,
mantiene aun así un grupo electrógeno para no depender de una sola fuente, una
organización que confía una función vital a un servicio remoto necesita un
recurso local.» Los cuatro términos (la red y el hospital de un lado, el servicio
remoto y la organización del otro) y la propiedad trasladada (la necesidad de un
respaldo cuando la infraestructura es vital) quedan claros, sin una sola letra ni
proporción. Y dices dónde se rompe: el grupo electrógeno vuelve a arrancar
idéntico, mientras que un recurso de software de reserva suele quedar degradado.

## 6. Coherencia y honestidad

- **No se inventa nada.** Se aclara y se desarrolla lo que está; no se añade
  ningún hecho no verificable. Donde la comprensión se detiene, se dice.
- **Marca el estado de la evidencia.** Distingue siempre lo *observado*, lo
  *medido*, lo *extrapolado* y lo *especulativo*; una afirmación empírica nunca
  aparece sin su grado de certeza.
- **No atribuyas intención sin señalarlo.** Nunca atribuyas voluntad ni agencia
  a un sistema como si fuera un hecho; si usas ese atajo, márcalo como tal.
- **El contraejemplo que enseña.** Una regla suele entenderse mejor en el punto
  donde se rompe: un caso real que salió mal, con cifras y con fuente, enseña
  más que el que salió bien. Dos condiciones para que sostenga en lugar de
  decorar: ilustra una tesis ya planteada, no la sustituye; se solidifica como
  cualquier referencia (cifras exactas, fuente primaria, un enlace que resuelve).
  Un contraejemplo aproximado se vuelve contra el argumento.
- **Una postura mesurada.** Sin excesos en ningún sentido; no te pases al bando
  que simplifica. A los autores se los moviliza como lecturas, no como adhesiones.
- **Un concepto, un solo lugar.** Una noción se define una vez; en otros sitios
  se remite a ella en vez de volver a desarrollarla. Nada contradice en silencio
  lo que se sostuvo antes.

## 7. La forma

- **Nada de rayas de puntuación.** Ni raya (el signo «—») ni semirraya (el signo
  «–») usadas como inciso. Se reescribe con comas, dos puntos, punto y coma,
  paréntesis, frases cortas. Los guiones de las palabras compuestas
  (teórico-práctico, físico-químico) se quedan.
- **Signos de apertura obligatorios.** Toda pregunta lleva sus dos signos, ¿ …
  ?, y toda exclamación los suyos, ¡ … !; abrir con el signo de cierre a secas
  es un calco del inglés que no se admite.
- **Comillas y espacios a la española.** En registro formal se prefieren las
  comillas angulares «…» (las inglesas "…" son aceptables); nunca se dejan
  espacios dentro de las comillas, al modo francés, ni un espacio antes de `;`,
  `:`, `?` o `!`. La coma y el punto van pegados a la palabra.
- **Ningún tic de máquina:** nada de «, y» ni de «, o» soldando dos oraciones
  (se corta la frase, o se pone punto y coma o dos puntos), nada de «En otras
  palabras», nada de regla de tres sistemática, nada de énfasis con cursivas por
  costumbre, nada de giros ampulosos.
- **Sin reflejo de antítesis.** El giro «no es X, es Y», «no X sino Y» puesto por
  automatismo es la firma de una plantilla. Consérvalo solo cuando la oposición
  es real y sostiene el argumento, nunca como efecto de balancín.
- **Sin frases maratón.** Una frase que pasa de unas diez líneas en pantalla
  obliga a un esfuerzo de lectura desproporcionado, por muy correcta que sea. Se
  parte en dos o se reestructura. Cuidado también con las listas disfrazadas,
  esas frases que ensartan una enumeración bajo una sintaxis continua: se hace
  una lista de verdad o frases separadas. La longitud no prueba la hondura.
- **Sin tic léxico.** Un mismo verbo o giro que vuelve una y otra vez
  («desplazar», «a la vez», «precisamente», «permite») delata la plantilla. Se
  rastrean los ecos por búsqueda y se varían, salvo cuando la repetición es un
  motivo buscado.
- **Registro sobrio, humano, cuidado.** Nunca «llmesco», «chatgptesco» ni
  «claudesco». La frase debe sonar a la de un autor, no a la de una plantilla.
- **A la caza de las marcas de ChatGPT.** Delatan a la máquina y se borran al
  releer:
  - aperturas huecas: «En el mundo actual», «En la era de», «Es importante
    señalar que», «Cabe destacar que», «No está de más recordar que»;
  - transiciones enchufadas al principio de la frase cuando ningún vínculo real
    las pide: «Además», «Asimismo», «Por otro lado», «En definitiva», «Por
    consiguiente»;
  - tics de reformulación: «En otras palabras», «Dicho de otro modo», «Dicho de
    otra manera»;
  - intensificadores vacíos puestos para dar peso: «verdaderamente»,
    «profundamente», «realmente», «sumamente», «fundamental», «crucial»,
    «clave»;
  - balancín reflejo: «no solo X sino también Y», «no se trata solo de X, sino
    también de Y»;
  - cierres huecos: «En conclusión», «En resumen», «A fin de cuentas», «En
    suma»;
  - abstracciones infladas: «el panorama de», «en el corazón de», «un punto de
    inflexión», «navegar por la complejidad de», «sumergirse en», «un antes y un
    después»;
  - simetría regular y ritmo ternario que alisan la prosa hasta el anonimato.

  El remedio no es otra fórmula prefabricada; es una frase situada, de ritmo
  irregular, que dice lo que hay que decir y nada más. La prosa de un autor tiene
  aristas.

## 8. El idioma

Lo más idiomático posible. Se prefiere siempre el giro que emplearía un
hispanohablante con letras al giro correcto pero plano. Español directo y
natural, con las convenciones propias del idioma: comillas angulares «…», signos
de apertura ¿ … ? y ¡ … !, tildes completas, y ningún espacio insecable a la
francesa antes de `; : ? !`.

## 9. Las fuentes

Ninguna referencia gratuita. Una cita dice qué establece la fuente, con qué
método, con qué límite, y por qué es decisiva en ese punto. Se lee de verdad la
fuente antes de usarla. Se destierran el «como bien dice X» y el name-dropping
decorativo. Una sola cita fuerte por afirmación.

A igual pertinencia, se equilibran las voces: cuando varias fuentes tienen la
misma autoridad, se citan de buen grado las autoras de referencia allí donde
existen. Nunca se retira una fuente por este motivo; es una atención al
equilibrio, no una cuota.

## 10. El bucle Ralph: fluidez por pares de párrafos

Un texto se relee no párrafo a párrafo, sino por pares de párrafos consecutivos,
porque la fluidez se juega en la costura, no dentro de un bloque. El bucle,
tomado del método «renderizar, mirar, corregir el código, repetir»:

1. **Lee en voz alta** el párrafo *n* seguido del párrafo *n+1*, de un tirón.
2. **Mira la costura:** ¿el paso de uno a otro se enlaza solo? ¿El primero pide
   el segundo? ¿Hay una repetición, un hueco lógico, un salto, una palabra
   repetida de un bloque a otro, una transición enchufada («además»,
   «asimismo») que tapa la ausencia de un vínculo real?
3. **Corrige la prosa, nunca la impresión:** toca el texto mismo (el orden de
   las frases, la última frase de *n*, la primera de *n+1*, una llamada de
   vuelta, un recorte); no te limites a anotar que «ahí chirría».
4. **Relee el par** y luego **avanza un paso:** deslízate al par (*n+1*, *n+2*) y
   empieza de nuevo. Las ventanas se solapan, de modo que cada párrafo se pone a
   prueba dos veces, una como llegada y otra como salida.

Sigue en un par hasta que la costura desaparezca; después pasa al siguiente. El
texto fluye cuando ninguna juntura se deja ver.

## 11. El gesto, en una imagen

El cocinero que **publica la receta** frente al chef que guarda el secreto:
muestra cada paso, del primer principio al resultado, para que el lector prepare
el plato solo. Un pasaje está listo cuando un lector no especialista, tras leerlo
una vez, sabría reexplicarlo a su vez.
