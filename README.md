# Hercules lua obfuscation Bot [![Discord Bot Invite](https://img.shields.io/badge/Invite-blue)](https://discord.com/oauth2/authorize?client_id=1293608330123804682)[![Discord Bots](https://top.gg/api/widget/servers/1293608330123804682.svg)](https://top.gg/bot/1293608330123804682)

**Hercules** is a powerful Lua obfuscator designed to make your Lua code nearly impossible to reverse-engineer. With multiple layers of advanced obfuscation techniques, Hercules ensures your scripts are secure from prying eyes.
Hercules is very much still in development and may not be the best yet, but we are committed to making it one of the best.

## Features

- **String Encoding:** Obfuscates strings by encoding them using a Caeser Cipher.
- **Variable Renaming:** Replaces variable names with randomly generated names.
- **Control Flow Obfuscation:** Adds fake control flow structures to confuse static analysis.
- **Garbage Code Insertion:** Injects junk code to bloat and obscure the script.
- **Bytecode Encoding:** Converts parts of a script into bytecode, making them harder to follow.
- **Function Inlining:** Integrates function code directly into calls, obscuring the original structure and logic. -> ***Broken atm***
- **Opaque Predicates:** Uses complex conditions that always evaluate to true or false, obscuring actual purpose.
- **Dynamic Code Generator:** Generates code blocks from the script itself, to complicate static analysis. -> ***Broken atm***

## Setup

### Classic Method

1. Ensure Python >=3.12 is installed. Download it [here](https://www.python.org/downloads/).
2. Clone this repository or download the zip file.
3. Open a terminal in the "Hercules" folder where you cloned the repository or extracted the zip file.
4. Run `git clone "https://github.com/zeusssz/hercules-obfuscator"` Obfuscator
5. Install luacheck with `luarocks install luacheck` if your on linux, or download it from [here](https://github.com/mpeterv/luacheck/releases/download/0.23.0/luacheck.exe) and put it at the location, where `main.py` is, if your on windows.
6. Run `pip install -r requirements.txt` to install the dependencies.
7. Open the file ".env.template" and complete all variables:
   - `TOKEN`: The token of your bot. Obtain it from the [Discord Developer Portal](https://discord.com/developers/applications).
   - `OWNER_ID`: Your Discord ID.
   - `SUPPORT_SERVER`: The ID of your support server. The bot must be a member of this server to create an invite if someone requires support.
8. Rename the file ".env.template" to ".env".
9. Run `python main.py` or `python3 main.py` to start the bot.

### Docker Method

#### Docker Compose Method

1. Open the `docker-compose.yml` file and update the environment variables as needed (such as `TOKEN`, `OWNER_ID`, and `SUPPORT_SERVER`).
2. In the terminal, run the following command from the `Hercules` folder to start the bot: `docker-compose up -d`.

#### Build the image yourself

1. Ensure Docker is installed. Download it from the [Docker website](https://docs.docker.com/get-docker/).
2. Clone this repository or download the zip file.
3. Open a terminal in the "Hercules" folder where you cloned the repository or extracted the zip file.
4. Run `docker build -t hercules .` to build the Docker image.

#### Use the pre-built image

1. Ensure Docker is installed. Download it from the [Docker website](https://docs.docker.com/get-docker/).
2. Open a terminal.
3. Run the bot with the command below:
   - Modify the variables according to your requirements.
   - Set the `TOKEN`, and `OWNER_ID`.

#### Run the bot
You only need to expose the port `-p 5000:5000`, if you want to use an external tool, to test, if the bot is running.
You need to call the `/health` endpoint.
```bash
docker run -d \
-e SUPPORT_SERVER=ID_OF_SUPPORTSERVER \
-e TOKEN=BOT_TOKEN \
-e OWNER_ID=DISCORD_ID_OF_OWNER \
--name Hercules \
--restart any \
--health-cmd="curl -f http://localhost:5000/health || exit 1" \
--health-interval=30s \
--health-timeout=10s \
--health-retries=3 \
--health-start-period=40s \
-p 5000:5000 \
-v hercules_log:/app/Hercules/Logs \
serpensin/hercules
```
