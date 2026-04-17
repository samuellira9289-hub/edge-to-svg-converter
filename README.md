# Otimizador SVG para Corte a Laser (Flask)

Este projeto é uma aplicação web Flask que permite otimizar imagens para corte a laser, utilizando detecção de bordas e conversão para formatos SVG e PLT (HPGL). Ele utiliza bibliotecas como OpenCV, NumPy e Pillow para o processamento de imagem.

## Estrutura do Projeto

```
. 
├── app.py
├── index.html
├── requirements.txt
├── Dockerfile
├── Procfile
├── render.yaml
├── railway.toml
└── README.md
```

- `app.py`: O código-fonte principal da aplicação Flask.
- `index.html`: O frontend da aplicação.
- `requirements.txt`: Lista das dependências Python do projeto.
- `Dockerfile`: Define o ambiente Docker para a aplicação, incluindo as dependências do sistema para OpenCV.
- `Procfile`: Usado por plataformas como Render e Railway para definir o comando de inicialização da aplicação.
- `render.yaml`: Arquivo de configuração para deploy na plataforma Render.
- `railway.toml`: Arquivo de configuração para deploy na plataforma Railway.
- `README.md`: Este arquivo, contendo as instruções de deploy.

## Deploy em Plataformas Gratuitas

Este guia detalha como fazer o deploy desta aplicação Flask em três plataformas populares de deploy gratuito: Railway, Render e Fly.io.

### Pré-requisitos Gerais

Antes de iniciar o deploy em qualquer plataforma, certifique-se de ter:

1.  **Conta nas plataformas:** Crie uma conta no [Railway](https://railway.app/), [Render](https://render.com/) e/ou [Fly.io](https://fly.io/).
2.  **Git:** O controle de versão Git instalado e configurado em sua máquina local.
3.  **Repositório Git:** Um repositório Git (por exemplo, no GitHub, GitLab ou Bitbucket) com o código deste projeto. Você precisará fazer o push de todos os arquivos (incluindo `Dockerfile`, `Procfile`, `render.yaml`, `railway.toml` e `requirements.txt`) para o seu repositório.

### 1. Deploy no Railway

O Railway é uma plataforma que simplifica o deploy de aplicações, detectando automaticamente a configuração do projeto através de `railway.toml` ou Nixpacks.

#### Passos para Deploy:

1.  **Crie um novo projeto no Railway:**
    *   Acesse o [dashboard do Railway](https://railway.app/dashboard).
    *   Clique em `New Project`.
    *   Selecione `Deploy from Git Repo`.
    *   Conecte sua conta Git (GitHub, GitLab, etc.) e selecione o repositório onde você fez o push deste projeto.
2.  **Configuração Automática:**
    *   O Railway detectará automaticamente o `railway.toml` e o `Dockerfile` (ou usará Nixpacks para construir a imagem).
    *   Ele usará o `startCommand` definido no `railway.toml` (`gunicorn --bind 0.0.0.0:$PORT --workers 4 app:app`) para iniciar sua aplicação.
3.  **Variáveis de Ambiente:**
    *   O Railway injeta automaticamente a variável de ambiente `PORT`.
    *   Se sua aplicação precisar de outras variáveis de ambiente, adicione-as na seção `Variables` do seu serviço no dashboard do Railway.
4.  **Acompanhe o Deploy:**
    *   O Railway iniciará o processo de build e deploy. Você pode acompanhar o progresso nos logs do serviço.
    *   Uma vez que o deploy for concluído, você receberá uma URL pública para acessar sua aplicação.

### 2. Deploy no Render

O Render é outra excelente plataforma para deploy de aplicações web, com suporte nativo a Docker e Python. O arquivo `render.yaml` simplifica a configuração.

#### Passos para Deploy:

1.  **Crie um novo serviço web no Render:**
    *   Acesse o [dashboard do Render](https://dashboard.render.com/).
    *   Clique em `New` -> `Web Service`.
    *   Conecte seu repositório Git e selecione o projeto.
2.  **Configuração via `render.yaml`:**
    *   O Render detectará automaticamente o arquivo `render.yaml` na raiz do seu repositório.
    *   Ele usará as configurações definidas lá para construir e implantar sua aplicação, incluindo o `buildCommand` (`pip install -r requirements.txt`) e o `startCommand` (`gunicorn --bind 0.0.0.0:$PORT --workers 4 app:app`).
3.  **Variáveis de Ambiente:**
    *   As variáveis `PYTHON_VERSION` e `PORT` já estão definidas no `render.yaml`.
    *   Se precisar de mais variáveis, adicione-as na seção `Environment` do seu serviço no dashboard do Render.
4.  **Acompanhe o Deploy:**
    *   O Render iniciará o build e deploy. Você pode ver os logs no dashboard.
    *   Após o deploy, sua aplicação estará acessível em uma URL fornecida pelo Render.

### 3. Deploy no Fly.io

O Fly.io foca em deploy de aplicações próximas aos usuários, utilizando máquinas virtuais leves. Ele também suporta Docker.

#### Passos para Deploy:

1.  **Instale o FlyCTL:**
    *   O Fly.io utiliza uma ferramenta de linha de comando chamada `flyctl`. Instale-a seguindo as instruções em [fly.io/docs/hands-on/install-flyctl/](https://fly.io/docs/hands-on/install-flyctl/).
2.  **Faça login no Fly.io:**
    ```bash
    flyctl auth login
    ```
3.  **Crie um novo aplicativo Fly.io:**
    *   Navegue até o diretório raiz do seu projeto no terminal.
    *   Execute o comando para lançar um novo aplicativo. Ele detectará seu `Dockerfile`.
    ```bash
    flyctl launch
    ```
    *   Siga as instruções. Você será solicitado a escolher um nome para o aplicativo e uma região.
    *   O `flyctl` irá gerar um arquivo `fly.toml` (semelhante ao `railway.toml` ou `render.yaml`) com as configurações do seu aplicativo. Verifique se a seção `[http_service]` está configurada para expor a porta correta (8000, conforme o Dockerfile e Gunicorn).
4.  **Deploy da Aplicação:**
    *   Após a configuração inicial, faça o deploy:
    ```bash
    flyctl deploy
    ```
    *   O Fly.io construirá a imagem Docker e a implantará em suas VMs.
5.  **Acompanhe o Deploy:**
    *   Você pode ver o status do deploy e os logs usando:
    ```bash
    flyctl logs
    ```
    *   Para obter a URL do seu aplicativo:
    ```bash
    flyctl info
    ```

## Considerações Finais

-   **Recursos Gratuitos:** Lembre-se de que as camadas gratuitas dessas plataformas têm limitações de recursos (CPU, RAM, tempo de execução). Monitore o uso para garantir que sua aplicação permaneça dentro dos limites.
-   **Variáveis de Ambiente:** Para informações sensíveis (chaves de API, etc.), **sempre** use variáveis de ambiente e **nunca** as inclua diretamente no código-fonte.
-   **Domínio Personalizado:** Todas as plataformas permitem configurar um domínio personalizado, caso você possua um.

Com esses arquivos e instruções, seu projeto Flask estará pronto para ser implantado e acessível publicamente!
