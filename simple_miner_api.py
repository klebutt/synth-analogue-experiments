from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Simple data storage
historical_data = {
    'stake_history': [],
    'request_history': [],
    'timestamps': []
}

def run_ssh_command(command):
    """Run a command on the remote server via SSH"""
    try:
        result = subprocess.run(
            f'ssh root@167.71.143.194 "{command}"',
            shell=True,
            capture_output=True,
            text=True,
            encoding='cp1252',
            errors='replace',
            timeout=5  # Very short timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        print(f"SSH Error: {e}")
        return "", str(e), 1

def get_basic_data():
    """Get only the most essential data"""
    data = {
        'status': 'unknown',
        'uptime': 'Unknown',
        'current_stake': 0.0,
        'stake_change_24h': 0.0,
        'wallet_balance': 0.0,
        'total_requests': 0,
        'requests_24h': 0,
        'last_request': 'Never',
        'memory_usage': 'Unknown',
        'cpu_usage': 'Unknown',
        'restart_count': 0,
        'last_updated': datetime.now().isoformat()
    }
    
    # Try to get miner status
    try:
        stdout, stderr, code = run_ssh_command("pm2 status | grep custom-miner")
        if code == 0 and "online" in stdout:
            data['status'] = 'online'
        elif code == 0 and "stopped" in stdout:
            data['status'] = 'stopped'
        else:
            data['status'] = 'offline'
    except:
        data['status'] = 'error'
    
    # Try to get stake info
    try:
        stdout, stderr, code = run_ssh_command("btcli stake list --wallet.name wallet1 --wallet.hotkey default | grep '50'")
        if code == 0 and stdout:
            # Look for stake value
            for line in stdout.split('\n'):
                if 'ש' in line and '50' in line:
                    try:
                        parts = line.split()
                        for part in parts:
                            if 'ש' in part and '.' in part:
                                stake_value = float(part.replace('ש', '').replace('‎', '').strip())
                                data['current_stake'] = stake_value
                                break
                    except:
                        pass
    except:
        pass
    
    # Try to get wallet balance
    try:
        stdout, stderr, code = run_ssh_command("btcli wallet overview --wallet.name wallet1 --wallet.hotkey default | grep 'Free Balance'")
        if code == 0 and stdout:
            try:
                balance_part = stdout.split('τ')[0].split()[-1]
                data['wallet_balance'] = float(balance_part)
            except:
                pass
    except:
        pass
    
    # Try to get request count
    try:
        stdout, stderr, code = run_ssh_command("pm2 logs custom-miner --lines 100 | grep -c 'Received prediction'")
        if code == 0 and stdout.strip().isdigit():
            data['total_requests'] = int(stdout.strip())
    except:
        pass
    
    # Calculate 24h change
    if data['current_stake'] > 0:
        if not historical_data['stake_history']:
            # First time - assume previous stake was 1 less (from your recent staking)
            data['stake_change_24h'] = 1.0
        else:
            data['stake_change_24h'] = data['current_stake'] - historical_data['stake_history'][0]
        
        # Store current data
        historical_data['stake_history'].append(data['current_stake'])
        historical_data['request_history'].append(data['total_requests'])
        historical_data['timestamps'].append(datetime.now().isoformat())
        
        # Keep only last 10 entries
        if len(historical_data['stake_history']) > 10:
            historical_data['stake_history'].pop(0)
            historical_data['request_history'].pop(0)
            historical_data['timestamps'].pop(0)
    
    return data

@app.route('/')
def serve_dashboard():
    """Serve the HTML dashboard"""
    return send_from_directory('.', 'miner_dashboard.html')

@app.route('/api/miner-data')
def get_miner_data():
    """API endpoint to get miner data"""
    try:
        data = get_basic_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/historical-data')
def get_historical_data():
    """Get historical data for charts"""
    return jsonify(historical_data)

if __name__ == '__main__':
    print("Starting Simple Miner Dashboard API...")
    print("Dashboard will be available at: http://localhost:5000")
    print("API endpoint: http://localhost:5000/api/miner-data")
    print("Manual refresh only - no auto-refresh")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
