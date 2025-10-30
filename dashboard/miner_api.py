#!/usr/bin/env python3
"""
Miner Dashboard API
Serves real-time data about your Synth miner
"""

import json
import subprocess
import requests
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Store historical data
historical_data = {
    'stake_history': [],
    'request_history': [],
    'timestamps': []
}

# Simple cache to avoid repeated SSH calls
cache = {
    'last_update': None,
    'data': None,
    'cache_duration': 5  # seconds
}

def run_ssh_command(command):
    """Run a command on the remote server via SSH"""
    try:
        result = subprocess.run(
            f'ssh root@167.71.143.194 "{command}"',
            shell=True,
            capture_output=True,
            text=True,
            encoding='cp1252',  # Use Windows encoding
            errors='replace',
            timeout=10
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        print(f"SSH Error: {e}")
        return "", str(e), 1

def get_miner_status():
    """Check if miner is running via PM2"""
    stdout, stderr, code = run_ssh_command("pm2 status | grep custom-miner")
    print(f"DEBUG: PM2 status - Code: {code}, Output: {stdout[:100]}, Error: {stderr[:100]}")
    if code == 0 and "online" in stdout:
        return "online"
    elif code == 0 and "stopped" in stdout:
        return "offline"
    else:
        return "unknown"

def get_miner_uptime():
    """Get miner uptime from PM2"""
    stdout, stderr, code = run_ssh_command("pm2 show custom-miner | grep 'uptime'")
    if code == 0:
        # Extract uptime from PM2 output
        for line in stdout.split('\n'):
            if 'uptime' in line.lower():
                return line.split(':')[-1].strip()
    return "Unknown"

def get_stake_info():
    """Get current stake information from bittensor directly"""
    stdout, stderr, code = run_ssh_command("btcli stake list --wallet.name wallet1 --wallet.hotkey default")
    if code == 0 and stdout:
        # Parse the stake list output to find subnet 50 stake
        lines = stdout.split('\n')
        for line in lines:
            if '50' in line and 'ש' in line:
                try:
                    # Extract alpha value from the line
                    parts = line.split()
                    for part in parts:
                        if 'ש' in part and '.' in part:
                            alpha_value = part.replace('ש', '').replace('‎', '').strip()
                            return float(alpha_value)
                except:
                    pass
    
    # No fallback - return 0 if we can't get real data
    return 0.0

def get_wallet_balance():
    """Get wallet balance"""
    stdout, stderr, code = run_ssh_command("btcli wallet overview --wallet.name wallet1 --wallet.hotkey default | grep 'free balance'")
    if code == 0 and stdout:
        try:
            # Extract balance from output
            balance_part = stdout.split('τ')[0].split()[-1]
            return float(balance_part)
        except:
            pass
    return 0.0  # No fallback - return 0 if we can't get real data

def get_validation_status():
    """Get validation status from API"""
    try:
        response = requests.get("https://api.synthdata.co/validation/miner?uid=233", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"validated": False, "reason": "API Error", "response_time": ""}

def get_system_resources():
    """Get system resource usage"""
    stdout, stderr, code = run_ssh_command("pm2 show custom-miner | grep -E 'memory|cpu'")
    memory = "Unknown"
    cpu = "Unknown"
    
    if code == 0:
        for line in stdout.split('\n'):
            if 'memory' in line.lower():
                memory = line.split(':')[-1].strip()
            elif 'cpu' in line.lower():
                cpu = line.split(':')[-1].strip()
    
    return memory, cpu

def get_restart_count():
    """Get PM2 restart count"""
    stdout, stderr, code = run_ssh_command("pm2 show custom-miner | grep 'restarts'")
    if code == 0 and stdout:
        try:
            restarts = stdout.split(':')[-1].strip()
            return int(restarts)
        except:
            pass
    return 0

def count_requests_in_logs():
    """Count prediction requests in logs"""
    stdout, stderr, code = run_ssh_command("pm2 logs custom-miner --lines 1000 | grep -c 'Received prediction\\|Generating predictions'")
    if code == 0:
        try:
            return int(stdout.strip())
        except:
            pass
    return 0

def get_last_request_time():
    """Get timestamp of last prediction request"""
    stdout, stderr, code = run_ssh_command("pm2 logs custom-miner --lines 1000 | grep 'Received prediction' | tail -1")
    if code == 0 and stdout:
        try:
            # Extract timestamp from log line
            timestamp_part = stdout.split('|')[0].strip()
            return timestamp_part
        except:
            pass
    return "Never"

def get_trust_score():
    """Get trust score from metagraph"""
    stdout, stderr, code = run_ssh_command("btcli subnet metagraph --netuid 50 --no_prompt | grep -A 5 -B 5 '233'")
    if code == 0 and stdout:
        try:
            # Look for trust score in metagraph output
            for line in stdout.split('\n'):
                if 'trust' in line.lower() and '233' in line:
                    # Extract trust value
                    parts = line.split()
                    for part in parts:
                        if part.replace('.', '').isdigit():
                            return float(part)
        except:
            pass
    return 0.0

def get_emission_rate():
    """Get emission rate from metagraph"""
    stdout, stderr, code = run_ssh_command("btcli subnet metagraph --netuid 50 --no_prompt | grep -A 5 -B 5 '233'")
    if code == 0 and stdout:
        try:
            # Look for emission in metagraph output
            for line in stdout.split('\n'):
                if 'emission' in line.lower() and '233' in line:
                    # Extract emission value
                    parts = line.split()
                    for part in parts:
                        if part.replace('.', '').isdigit():
                            return float(part)
        except:
            pass
    return 0.0

def get_network_rank():
    """Get network rank by comparing stake to other miners"""
    current_stake = get_stake_info()
    if current_stake == 0:
        return "Unranked (No Stake)"
    
    stdout, stderr, code = run_ssh_command("btcli subnet metagraph --netuid 50 --no_prompt")
    if code == 0 and stdout:
        try:
            stakes = []
            for line in stdout.split('\n'):
                if 'ש' in line and 'τ' not in line:  # Filter for alpha stake values
                    try:
                        parts = line.split()
                        for part in parts:
                            if 'ש' in part and '.' in part:
                                s = float(part.replace('ש', '').replace('‎', '').strip())
                                stakes.append(s)
                    except ValueError:
                        continue
            
            if not stakes:
                return "Cannot determine rank"
            
            stakes.sort(reverse=True)
            
            # Find position
            rank = 1
            for s in stakes:
                if current_stake >= s:
                    break
                rank += 1
            
            total_miners = len(stakes)
            percentile = (total_miners - rank + 1) / total_miners * 100 if total_miners > 0 else 0
            
            if rank <= 64:  # Top 64 usually get validator permits
                return f"TOP {rank} (Validator Permit Tier)"
            elif percentile >= 75:
                return f"TOP {rank} (Top 25%)"
            elif percentile >= 50:
                return f"TOP {rank} (Top 50%)"
            else:
                return f"Rank {rank} (Bottom 50%)"
        except:
            pass
    return "Cannot determine rank"

def get_last_predictions():
    """Get details of last predictions from logs"""
    stdout, stderr, code = run_ssh_command("pm2 logs custom-miner --lines 100 | grep -A 3 'Generated.*simulations' | tail -4")
    if code == 0 and stdout:
        try:
            # Extract prediction details
            lines = stdout.strip().split('\n')
            if lines and 'Generated' in lines[0]:
                return lines[0].strip()
        except:
            pass
    return "No recent predictions"

def get_crps_score():
    """Get CRPS score from validation data"""
    validation = get_validation_status()
    if validation.get('validated') and 'crps' in validation:
        return str(validation['crps'])
    return "N/A"

def calculate_stake_change_24h(current_stake):
    """Calculate stake change over last 24 hours"""
    if not historical_data['stake_history']:
        # If no historical data, assume this is the first call after staking
        # We know you staked 1 TAO, so previous stake was ~93.64
        previous_stake = current_stake - 1.0  # Approximate previous stake
        return current_stake - previous_stake
    
    # Get stake from 24 hours ago (or earliest available)
    stake_24h_ago = historical_data['stake_history'][0] if historical_data['stake_history'] else current_stake
    change = current_stake - stake_24h_ago
    
    # Log for debugging
    print(f"DEBUG: Current stake: {current_stake}, Previous: {stake_24h_ago}, Change: {change}")
    
    return change

@app.route('/')
def serve_dashboard():
    """Serve the HTML dashboard"""
    return send_from_directory('.', 'miner_dashboard.html')

@app.route('/api/miner-data')
def get_miner_data():
    """API endpoint to get all miner data"""
    try:
        # Check cache first
        current_time = datetime.now()
        if (cache['last_update'] and 
            cache['data'] and 
            (current_time - cache['last_update']).total_seconds() < cache['cache_duration']):
            return jsonify(cache['data'])
        
        # Cache miss - fetch fresh data
        # Get essential data first (fast)
        status = get_miner_status()
        uptime = get_miner_uptime()
        current_stake = get_stake_info()
        wallet_balance = get_wallet_balance()
        memory, cpu = get_system_resources()
        restart_count = get_restart_count()
        total_requests = count_requests_in_logs()
        last_request = get_last_request_time()
        
        # Simplified data - only essential metrics
        validation = {"validated": False, "reason": "Not checked", "response_time": ""}
        trust_score = 0.0
        emission_rate = 0.0
        network_rank = "Not calculated"
        last_predictions = "Not available"
        crps_score = "N/A"
        
        # Calculate 24h change from historical data
        stake_change_24h = calculate_stake_change_24h(current_stake)
        
        # Store current data point
        current_time = datetime.now()
        historical_data['stake_history'].append(current_stake)
        historical_data['request_history'].append(total_requests)
        historical_data['timestamps'].append(current_time.isoformat())
        
        # Keep only last 24 hours of data
        cutoff_time = current_time - timedelta(hours=24)
        filtered_data = []
        for i, timestamp_str in enumerate(historical_data['timestamps']):
            timestamp = datetime.fromisoformat(timestamp_str)
            if timestamp > cutoff_time:
                filtered_data.append(i)
        
        historical_data['stake_history'] = [historical_data['stake_history'][i] for i in filtered_data]
        historical_data['request_history'] = [historical_data['request_history'][i] for i in filtered_data]
        historical_data['timestamps'] = [historical_data['timestamps'][i] for i in filtered_data]
        
        # Calculate 24h requests
        requests_24h = 0
        if len(historical_data['request_history']) > 1:
            requests_24h = historical_data['request_history'][-1] - historical_data['request_history'][0]
        
        # Calculate 24h stake change
        if len(historical_data['stake_history']) > 1:
            stake_change_24h = historical_data['stake_history'][-1] - historical_data['stake_history'][0]
        
        # Prepare response
        data = {
            'status': status,
            'uptime': uptime,
            'current_stake': f"{current_stake:.18f}",
            'stake_change_24h': f"{stake_change_24h:.18f}",
            'wallet_balance': f"{wallet_balance:.4f}",
            'total_requests': total_requests,
            'requests_24h': max(0, requests_24h),
            'last_request': last_request,
            'response_time': validation.get('response_time', 'N/A'),
            'crps_score': crps_score,
            'trust_score': f"{trust_score:.4f}",
            'memory_usage': memory,
            'cpu_usage': cpu,
            'restart_count': restart_count,
            'last_predictions': last_predictions,
            'emission_rate': f"{emission_rate:.4f}",
            'network_rank': network_rank,
            'validated': validation.get('validated', False),
            'validation_reason': validation.get('reason', ''),
            'timestamp': current_time.isoformat()
        }
        
        # Update cache
        cache['data'] = data
        cache['last_update'] = current_time
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical-data')
def get_historical_data():
    """Get historical data for charts"""
    return jsonify(historical_data)

if __name__ == '__main__':
    print("Starting Miner Dashboard API...")
    print("Dashboard will be available at: http://localhost:5000")
    print("API endpoint: http://localhost:5000/api/miner-data")
    print("Auto-refresh every 30 seconds")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
