# Hercules lua obfuscation Bot [![Discord Bot Invite](https://img.shields.io/badge/Invite-blue)](https://discord.com/oauth2/authorize?client_id=1293608330123804682)[![Discord Bots](https://top.gg/api/widget/servers/1293608330123804682.svg)](https://top.gg/bot/1293608330123804682)

>[!NOTE]
**Hercules** is a powerful Lua obfuscator designed to make your Lua code nearly impossible to reverse-engineer. With multiple layers of advanced obfuscation techniques, Hercules ensures your scripts are secure from prying eyes.
Hercules is very much still in development and may not be the best yet, but we are committed to making it one of the best.
Keep in mind that this is just the bot for the obfuscator. If you want to take a look into the obfuscator itself, you can check it out [here](https://github.com/zeusssz/hercules-obfuscator).
## Features

- **Control Flow:** Adds fake control flow structures to confuse static analysis. *(Enabled)*
- **Variable Renaming:** Replaces variable names with randomly generated names. *(Enabled)*
- **Garbage Code:** Injects junk code to bloat and obscure the script. *(Enabled)*
- **Opaque Predicates:** Uses complex conditions that always evaluate to true or false, obscuring the actual purpose. *(Enabled)*
- **Bytecode Encoding:** Converts parts of a script into bytecode, making them harder to follow. *(Disabled)*
- **String Encoding:** Obfuscates strings by encoding them using a Caesar Cipher. *(Disabled)*
- **Code Compressor:** Compresses code to reduce its size and further obfuscate its structure. *(Enabled)*
- **String to Expression:** Converts strings to expressions to complicate static analysis. *(Disabled)*
- **Virtual Machine:** Executes parts of the code in a virtualized environment for additional obfuscation. *(Enabled)*
- **Function Wrapping:** Wraps functions in additional layers to obscure functionality. *(Enabled)*
- **Function Inlining:** Integrates function code directly into calls, obscuring the original structure and logic. *(Disabled)*
- **Dynamic Code:** Generates code blocks from the script itself to complicate static analysis. *(Disabled)*

## Setup

### Classic Method

1. Ensure Python >=3.12 is installed. Download it [here](https://www.python.org/downloads/).
2. Run `git clone https://github.com/Serpensin/DiscordBots-Hercules.git HerculesBot && cd HerculesBot/Hercules`.
3. Run `git clone "https://github.com/zeusssz/hercules-obfuscator.git" Obfuscator`
4. Install luacheck
    - **Windows:**
        - Install luacheck with:
          ```cmd
          curl -L -o luacheck.exe "https://github.com/mpeterv/luacheck/releases/download/0.23.0/luacheck.exe"
          ```
    - **Linux:**
        - Install lua with:
          ```bash
          sudo apt install lua5.4 liblua5.4-dev
          ```
        - Install luarocks with:
          ```bash
          sudo apt install luarocks
          ```
        - Install luacheck with:
          ```bash
          sudo luarocks-5.4 install luacheck
          ```
5. Run `pip install -r requirements.txt` to install the required Python packages.
6. Open the file ".env.template" and complete all variables:
   - `TOKEN`: The token of your bot. Obtain it from the [Discord Developer Portal](https://discord.com/developers/applications).
   - `OWNER_ID`: Your Discord ID.
   - `SUPPORT_SERVER`: The ID of your support server. The bot must be a member of this server to create an invite if someone requires support.
7. Rename the file ".env.template" to ".env".
8. Run `python main.py` or `python3 main.py` to start the bot.

### Docker Method

#### Docker Compose Method (Recommended)

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
ghcr.io/serpensin/discordbots-hercules:latest
```
