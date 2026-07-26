import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class CakeCityApi {
  CakeCityApi({String? baseUrl}) : baseUrl = baseUrl ?? const String.fromEnvironment('API_URL', defaultValue: 'https://cakecity-api.onrender.com');
  final String baseUrl;
  final _storage = const FlutterSecureStorage();
  String? _access;

  Future<dynamic> request(String path, {String method = 'GET', Object? body, Map<String, String>? headers, bool retry = true}) async {
    final response = http.Request(method, Uri.parse('$baseUrl$path'))
      ..headers.addAll({'Content-Type': 'application/json', if (_access != null) 'Authorization': 'Bearer $_access', ...?headers})
      ..body = body == null ? '' : jsonEncode(body);
    var result = await response.send();
    if (result.statusCode == 401 && retry && await refresh()) {
      return request(path, method: method, body: body, headers: headers, retry: false);
    }
    final text = await result.stream.bytesToString();
    final decoded = text.isEmpty ? null : jsonDecode(text);
    if (result.statusCode < 200 || result.statusCode >= 300) {
      throw Exception(decoded is Map ? decoded['detail'] ?? 'Request failed' : 'Request failed');
    }
    return decoded;
  }

  Future<void> login(String email, String password) async {
    final data = await request('/v1/auth/mobile/login', method: 'POST', body: {'email': email, 'password': password}, retry: false);
    if (data['customer']['role'] != 'driver') throw Exception('This account is not a driver account');
    _access = data['access_token'];
    await _storage.write(key: 'refresh_token', value: data['refresh_token']);
  }

  Future<bool> restore() async => (await _storage.read(key: 'refresh_token')) != null && await refresh();

  Future<bool> refresh() async {
    final token = await _storage.read(key: 'refresh_token');
    if (token == null) return false;
    try {
      final data = await request('/v1/auth/mobile/refresh', method: 'POST', body: {'refresh_token': token}, retry: false);
      _access = data['access_token'];
      await _storage.write(key: 'refresh_token', value: data['refresh_token']);
      return true;
    } catch (_) { await _storage.deleteAll(); return false; }
  }

  Future<void> logout() async {
    final token = await _storage.read(key: 'refresh_token');
    if (token != null) {
      try { await request('/v1/auth/mobile/logout', method: 'POST', body: {'refresh_token': token}, retry: false); } catch (_) {}
    }
    _access = null; await _storage.deleteAll();
  }

  Future<String> uploadProof(Uint8List bytes) async {
    final signed = await request('/v1/driver/uploads/signature');
    final upload = http.MultipartRequest('POST', Uri.parse(signed['upload_url']))
      ..fields.addAll({
        'api_key': signed['api_key'], 'timestamp': '${signed['timestamp']}',
        'folder': signed['folder'], 'signature': signed['signature'],
      })
      ..files.add(http.MultipartFile.fromBytes('file', bytes, filename: 'proof-${DateTime.now().millisecondsSinceEpoch}.png'));
    final result = await upload.send();
    final payload = jsonDecode(await result.stream.bytesToString());
    if (result.statusCode < 200 || result.statusCode >= 300) throw Exception('Proof upload failed');
    return payload['secure_url'];
  }
}
