// ==========================================
// CAPTURA DOS ELEMENTOS
// ==========================================

const conversa = document.getElementById("conversa");
const listaMensagens = document.getElementById("listaMensagens");
const mensagemInicial = document.getElementById("mensagemInicial");
const digitando = document.getElementById("digitando");
const inputPergunta = document.getElementById("inputPergunta");
const botaoEnviar = document.getElementById("botaoEnviar");


// ==========================================
// VARIÁVEIS
// ==========================================

let historico = [];


// ==========================================
// SESSÃO
// ==========================================

let sessaoId = sessionStorage.getItem("sessao_id");

if (!sessaoId) {

    sessaoId = crypto.randomUUID();

    sessionStorage.setItem(
        "sessao_id",
        sessaoId
    );
}


// ==========================================
// DIGITANDO
// ==========================================

digitando.style.display = "none";


// ==========================================
// EVENTOS
// ==========================================

botaoEnviar.addEventListener(
    "click",
    enviarPergunta
);

inputPergunta.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Enter") {

            event.preventDefault();

            enviarPergunta();

        }

    }
);


// ==========================================
// BOTÕES DE SUGESTÃO
// ==========================================

const categorias = document.querySelectorAll(
    ".sugestao-btn"
);

categorias.forEach(botao => {

    botao.addEventListener(
        "click",
        () => {

            botao.classList.toggle("ativo");

            const submenu =
                botao.nextElementSibling;

            if (submenu) {

                submenu.classList.toggle(
                    "ativo"
                );

            }

        }
    );

});


const perguntas = document.querySelectorAll(
    ".pergunta"
);

perguntas.forEach(pergunta => {

    pergunta.addEventListener(
        "click",
        () => {

            inputPergunta.value =
                pergunta.textContent.trim();

            inputPergunta.focus();

            botaoEnviar.click();

        }
    );

});


// ==========================================
// ENVIAR PERGUNTA
// ==========================================

async function enviarPergunta() {

    const pergunta =
        inputPergunta.value.trim();

    if (pergunta === "") {
        return;
    }


    if (mensagemInicial) {

        mensagemInicial.style.display =
            "none";

    }


    // ==========================================
    // MOSTRA PERGUNTA
    // ==========================================

    adicionarMensagem(
        pergunta,
        "usuario"
    );


    // ==========================================
    // HISTÓRICO
    // ==========================================


    const historicoAnterior = [...historico];

    // Adiciona a pergunta atual ao histórico local.
    historico.push({
        autor: "usuario",
        texto: pergunta
    });

    inputPergunta.value = "";


    // ==========================================
    // MOSTRA DIGITANDO
    // ==========================================

    digitando.style.display = "flex";

    rolarConversa();


    try {

        console.log(
            "Enviando pergunta..."
        );


        const resposta = await fetch(
            "/chat",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    pergunta: pergunta,
                    historico: historicoAnterior,
                    sessao_id: sessaoId
                })
            }
        );


        console.log(
            "Status:",
            resposta.status
        );


        if (!resposta.ok) {

            throw new Error(
                `Erro HTTP: ${resposta.status}`
            );

        }


        const dados =
            await resposta.json();


        console.log(
            "Dados recebidos:",
            dados
        );


        // ==========================================
        // RESPOSTA
        // ==========================================

        adicionarMensagem(
            dados.resposta,
            "bot",
            dados.fontes || []
        );


        // ==========================================
        // HISTÓRICO
        // ==========================================

        historico.push({

            autor: "bot",

            texto: dados.resposta

        });


        if (historico.length > 20) {

            historico =
                historico.slice(-20);

        }


        rolarConversa();


    } catch (erro) {

        console.error(
            "ERRO:",
            erro
        );


        adicionarMensagem(
            `Erro ao conectar com o servidor: ${erro.message}`,
            "sistema"
        );


    } finally {

        // ==========================================
        // SEMPRE ESCONDE O DIGITANDO
        // ==========================================

        digitando.style.display = "none";

    }

}


// ==========================================
// ADICIONAR MENSAGEM
// ==========================================

function adicionarMensagem(
    texto,
    tipo,
    fontes = []
) {

    const mensagem =
        document.createElement("div");


    mensagem.classList.add(
        "mensagem"
    );

    mensagem.classList.add(
        tipo
    );


    // ==========================================
    // TEXTO
    // ==========================================

    const textoMensagem =
        document.createElement("div");


    textoMensagem.classList.add(
        "texto-mensagem"
    );


    textoMensagem.innerText =
        texto;


    mensagem.appendChild(
        textoMensagem
    );


    // ==========================================
    // FONTES
    // ==========================================

    if (
        tipo === "bot" &&
        Array.isArray(fontes) &&
        fontes.length > 0
    ) {

        const botaoFontes =
            document.createElement(
                "button"
            );


        botaoFontes.classList.add(
            "botao-fontes"
        );


        botaoFontes.type = "button";


        botaoFontes.innerText =
            `📚 Fontes (${fontes.length})`;


        // ==========================================
        // LISTA
        // ==========================================

        const listaFontes =
            document.createElement(
                "div"
            );


        listaFontes.classList.add(
            "lista-fontes"
        );


        fontes.forEach(
            (fonte, index) => {

                const fonteDiv =
                    document.createElement(
                        "div"
                    );


                fonteDiv.classList.add(
                    "fonte"
                );


                const titulo =
                    fonte.titulo ||
                    fonte.arquivo ||
                    "Documento";


                const arquivo =
                    fonte.arquivo || "";


                fonteDiv.innerHTML = `
                    <strong>
                        📄 ${index + 1}. ${titulo}
                    </strong>
                    <br>
                `;


                if (arquivo) {

                    const link =
                        document.createElement(
                            "a"
                        );


                    link.href =
                        `/documentos/${encodeURIComponent(
                            arquivo
                        )}`;


                    link.target =
                        "_blank";


                    link.rel =
                        "noopener noreferrer";


                    link.innerText =
                        "Abrir documento ↗";


                    fonteDiv.appendChild(
                        link
                    );

                }


                listaFontes.appendChild(
                    fonteDiv
                );

            }
        );


        // ==========================================
        // ABRIR / FECHAR
        // ==========================================

        botaoFontes.addEventListener(
            "click",
            () => {

                listaFontes.classList.toggle(
                    "ativo"
                );

            }
        );


        mensagem.appendChild(
            botaoFontes
        );


        mensagem.appendChild(
            listaFontes
        );

    }


    listaMensagens.appendChild(
        mensagem
    );

}


// ==========================================
// ROLAR CONVERSA
// ==========================================

function rolarConversa() {

    conversa.scrollTop =
        conversa.scrollHeight;

}