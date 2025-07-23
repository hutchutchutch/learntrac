from flask import Flask, jsonify
import os
import socket

app = Flask(__name__)

@app.route('/trac/login')
def health():
    """Health check endpoint expected by ALB"""
    return 'OK', 200

@app.route('/')
def root():
    return jsonify({
        'service': 'trac-test',
        'version': 'test',
        'hostname': socket.gethostname(),
        'status': 'healthy'
    })

@app.route('/trac/')
def trac_root():
    return 'Trac Test Container - Main Page', 200

@app.route('/wiki/<path:path>')
def wiki(path):
    return 'Trac Wiki Test - Path: {}'.format(path), 200

@app.route('/ticket/<int:ticket_id>')
def ticket(ticket_id):
    return 'Trac Ticket Test - ID: {}'.format(ticket_id), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)