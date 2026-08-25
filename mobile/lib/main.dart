import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() => runApp(const OdyssyApp());

class OdyssyApp extends StatelessWidget {
  const OdyssyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Odyssy',
      theme: ThemeData.dark(useMaterial3: true),
      home: const MainScreen(),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  final TextEditingController _ipController = TextEditingController(text: '192.168.');
  WebSocketChannel? _channel;
  String _content = '';
  String _status = 'Disconnected';

  void _connect() {
    _channel?.sink.close();
    final ip = _ipController.text;
    final url = 'ws://$ip:8000/ws';
    setState(() => _status = 'Connecting to $url...');
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      setState(() => _status = 'Connected');
      
      _channel!.stream.listen((message) {
        final msg = jsonDecode(message);
        setState(() {
          if (msg['type'] == 'status') {
            _content = '*${msg['data']}*\n\n';
          } else if (msg['type'] == 'token') {
            _content += msg['data'];
          } else if (msg['type'] == 'error') {
            _content = 'Error: ${msg['data']}';
          } else if (msg['type'] == 'done') {
            _content += '\n\n[Done]';
          }
        });
      }, onDone: () {
        setState(() => _status = 'Disconnected');
      }, onError: (e) {
        setState(() => _status = 'Error: $e');
      });
    } catch (e) {
      setState(() => _status = 'Error: $e');
    }
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Odyssy')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _ipController,
                    decoration: const InputDecoration(labelText: 'Laptop IP Address'),
                  ),
                ),
                const SizedBox(width: 16),
                ElevatedButton(
                  onPressed: _connect,
                  child: const Text('Connect'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(_status, style: TextStyle(
              color: _status == 'Connected' ? Colors.green : Colors.redAccent
            )),
            const Divider(),
            Expanded(
              child: SingleChildScrollView(
                child: SelectableText(_content, style: const TextStyle(fontSize: 16)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
