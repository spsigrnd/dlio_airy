#!/usr/bin/env python3
from flask import Flask, render_template, jsonify, request
import subprocess
import threading
import time
import os
import signal
from datetime import datetime

app = Flask(__name__)

# Terminal configurations
terminals = {
    1: {
        'name': 'DLIO',
        'command': 'cd /home/nvidia/dlio_ws && source devel/setup.bash && roslaunch direct_lidar_inertial_odometry dlio.launch rviz:=false pointcloud_topic:=/rslidar_points imu_topic:=/rslidar_imu_data',
        'delay': 3,
        'running': False,
        'pid': None
    },
    2: {
        'name': 'Mavros to Pixhawk',
        'command': 'roslaunch mavros apm.launch fcu_url:=/dev/ttyUSB0:921600',
        'delay': 2,
        'running': False,
        'pid': None
    },
    3: {
        'name': 'Airy SDK',
        'command': 'cd /home/nvidia/dlio_ws && source devel/setup.bash && roslaunch rslidar_sdk start.launch',
        'delay': 3,
        'running': False,
        'pid': None
    },
    4: {
        'name': 'Save DLIO Output',
        'command': 'python3 /home/nvidia/dlio_ws/src/saverostopic.py',
        'delay': 1,
        'running': False,
        'pid': None
    },
    5: {
        'name': 'DLIO to Mavros Publisher',
        'command': 'python3 /home/nvidia/dlio_ws/src/dlio-Mavros_bridge/scripts/test13.py',
        'delay': 1,
        'running': False,
        'pid': None
    },
    6: {
        'name': 'Save PCAP File',
        'command': 'tshark -i eth0 -w /home/nvidia/FLASK_CSD/PCAP_tshark/capture_$(date +%Y%m%d_%H%M%S).pcap',
        'delay': 1,
        'running': False,
        'pid': None
    }
}

def send_command_to_terminal(term_num, command):
    """Send command to specific terminal"""
    try:
        with open(f'/tmp/terminal_{term_num}_in', 'w') as f:
            f.write(command + '\n')
        return True
    except:
        return False

def get_terminal_output(term_num, lines=5):
    """Get last few lines from terminal output"""
    try:
        # This is a simplified version - in real implementation you'd need to capture output properly
        result = subprocess.run(['tail', '-n', str(lines), f'/tmp/terminal_{term_num}_out'], 
                              capture_output=True, text=True, timeout=2)
        return result.stdout
    except:
        return "No output available"

@app.route('/')
def index():
    return render_template('index.html', terminals=terminals)

@app.route('/api/status')
def status():
    return jsonify({
        'terminals': terminals,
        'server_connected': True,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/terminal/<int:term_num>/start', methods=['POST'])
def start_terminal(term_num):
    if term_num not in terminals:
        return jsonify({'success': False, 'message': 'Invalid terminal number'})
    
    success = send_command_to_terminal(term_num, terminals[term_num]['command'])
    if success:
        terminals[term_num]['running'] = True
        time.sleep(terminals[term_num]['delay'])
    
    return jsonify({'success': success, 'running': terminals[term_num]['running']})

@app.route('/api/terminal/<int:term_num>/stop', methods=['POST'])
def stop_terminal(term_num):
    if term_num not in terminals:
        return jsonify({'success': False, 'message': 'Invalid terminal number'})
    
    # Send Ctrl+C equivalent
    success = send_command_to_terminal(term_num, '\x03')
    if success:
        terminals[term_num]['running'] = False
    
    return jsonify({'success': success, 'running': terminals[term_num]['running']})

@app.route('/api/terminal/<int:term_num>/output')
def get_output(term_num):
    output = get_terminal_output(term_num, 5)
    return jsonify({'output': output, 'terminal': term_num})

@app.route('/api/master/start', methods=['POST'])
def master_start():
    results = {}
    for term_num in sorted(terminals.keys()):
        success = send_command_to_terminal(term_num, terminals[term_num]['command'])
        terminals[term_num]['running'] = success
        results[term_num] = success
        time.sleep(terminals[term_num]['delay'])
    
    return jsonify({'success': True, 'results': results})

@app.route('/api/master/stop', methods=['POST'])
def master_stop():
    results = {}
    for term_num in terminals.keys():
        success = send_command_to_terminal(term_num, '\x03')
        terminals[term_num]['running'] = not success
        results[term_num] = success
    
    return jsonify({'success': True, 'results': results})

def start_terminals_automatically():
    """Function to automatically start terminals when server starts"""
    time.sleep(2)  # Wait for server to fully start
    subprocess.Popen(['/home/nvidia/auto_terminals.sh'])

if __name__ == '__main__':
    # Start terminals automatically when flask starts
    auto_thread = threading.Thread(target=start_terminals_automatically, daemon=True)
    auto_thread.start()
    
    app.run(host='0.0.0.0', port=5001, debug=True)