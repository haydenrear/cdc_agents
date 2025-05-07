deactivate
rm -rf .cdc_agents
python3 -m venv .cdc_agents
source .cdc_agents/bin/activate
pip install -r requirements.txt