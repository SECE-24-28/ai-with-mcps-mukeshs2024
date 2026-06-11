MULTI-AGENT DATA ANALYSIS PIPELINE
==================================

DETAILED OVERVIEW
-----------------
The Multi-Agent Data Analysis Pipeline is a state-of-the-art intelligent automation system designed to eliminate the manual labor associated with data processing. In today's data-driven world, analysts spend countless hours cleaning, formatting, and analyzing raw datasets. This project solves that bottleneck by employing a swarm of specialized Artificial Intelligence agents that work together in a synchronized sequence.

By simply providing a raw CSV dataset, the system automatically routes the data through a series of specialized nodes. It performs comprehensive data validation, intelligent cleaning, deep statistical analysis, and automated visualization, outputting a business-ready Excel report and graphical charts without requiring any manual intervention.


SYSTEM DESCRIPTION
------------------
The system is built on top of the Google Agent Development Kit (ADK) framework and utilizes the Google Gemini Large Language Model as its cognitive engine.

Instead of relying on a single, monolithic AI model to perform all tasks, this pipeline embraces the "Multi-Agent System" philosophy combined with the Model Context Protocol (MCP). Each of the four specialized agents connects to its own dedicated MCP server over a stdio transport. This means every agent communicates with its tools through a standardized, protocol-driven interface rather than direct Python function calls.

MCP (Model Context Protocol) is an open standard that defines how AI agents discover and invoke tools. Each MCP server in this project is a lightweight FastMCP process that exposes one or more tools. The agent sends a JSON-RPC request to the server, the server executes the tool, and returns a structured response. This separation makes tools independently deployable, testable, and replaceable without touching the agent logic.

The pipeline natively supports reading raw CSV files, executing data processing scripts in a secure subprocess sandbox, generating graphical charts, and assembling multi-sheet Excel files using Pandas.


ARCHITECTURE
------------
The architecture follows a sequential, hierarchical delegation pattern where each agent is decoupled from its tools via an MCP server.

1. The Orchestrator Node
The entry point of the system. It receives the user's initial prompt, understands the end goal, and acts as the project manager. It holds the map of all available sub-agents and knows exactly when to trigger them in the correct sequence. It does not connect to any MCP server directly.

2. The Data Loader Node
Connected to the data-loader-server MCP process. Its sole architectural purpose is to ingest the CSV, map the column headers, detect data types (integers, floats, categorical strings), and identify structural issues like missing rows before passing the metadata back to the orchestrator.

3. The Data Cleaner Node
Connected to the data-cleaner-server MCP process. It receives the metadata and executes targeted scripts to fill missing values, strip whitespace, remove duplicate entries, and normalize text casing. It writes the clean data to a secure temporary file.

4. The Analyst Node
Connected to the analyst-server MCP process. It reads the cleaned data and performs statistical aggregations, correlation matrix generation, and outlier detection. It generates human-readable business insights based on the mathematical results.

5. The Visualizer Node
Connected to the visualizer-server MCP process. It takes the insights and the clean data to generate PNG graphical charts (trend lines, distribution histograms, comparison bar charts) and compiles everything into a final Excel workbook.


MCP SERVER STRUCTURE
--------------------
Each MCP server lives in the mcp_servers/ directory and is a standalone Python script:

    mcp_servers/
        data_loader_server.py   -- exposes load_csv_file and get_data_preview
        data_cleaner_server.py  -- exposes clean_data
        analyst_server.py       -- exposes analyze_data
        visualizer_server.py    -- exposes create_visualizations

Each server is launched as a subprocess by the ADK runtime via StdioServerParameters. The agent discovers the available tools automatically by querying the MCP server on startup. Communication happens over stdin/stdout using the JSON-RPC 2.0 protocol defined by MCP.


WORKFLOW IN DEPTH
-----------------
Step A: User Input
The user interacts with the ADK Web Interface and submits a prompt containing the path to the raw data file.

Step B: Routing
The Orchestrator receives the request and transfers control to the Data Loader.

Step C: MCP Tool Invocation
The Data Loader agent sends a JSON-RPC call to its MCP server (data_loader_server.py) to invoke the load_csv_file tool. The server runs the function and returns a structured JSON result back to the agent.

Step D: Processing
The Orchestrator passes the file path to the Data Cleaner agent, which calls its MCP server to run the clean_data tool. The cleaned dataset is saved to output/cleaned_data.csv.

Step E: Analysis and Visualization
The Analyst agent calls its MCP server to run analyze_data on the cleaned file. The Visualizer agent then calls its MCP server to run create_visualizations, producing PNG chart files and an analysis_report.xlsx in the output/ directory.

Step F: Completion
The Orchestrator collects all results and returns a final summary message to the user.


SETUP AND DEPLOYMENT
--------------------
Step 1: Obtain a Gemini API Key from Google AI Studio.
Step 2: Create a .env file in the root directory and add: GEMINI_API_KEY=your_key_here
Step 3: Activate your Python virtual environment.
Step 4: Install the required dependencies using: pip install -r requirements.txt
Step 5: Launch the local web server using the command: adk web multi_agent_pipeline
Step 6: Navigate to the local host address in your web browser to interact with the pipeline.

Note: The ADK runtime automatically starts and manages each MCP server subprocess when an agent needs its tools. No manual server startup is required.


PROJECT STRUCTURE
-----------------
    adk-multiagent-project/
        multi_agent_pipeline/
            agent.py            -- agent definitions wired to MCP servers
            tools/              -- core tool logic (imported by MCP servers)
                data_loader.py
                data_cleaner.py
                analyst.py
                visualizer.py
        mcp_servers/            -- MCP server entry points (one per agent)
            data_loader_server.py
            data_cleaner_server.py
            analyst_server.py
            visualizer_server.py
        data/                   -- input data files
        output/                 -- generated charts and Excel reports
        requirements.txt
        .env
