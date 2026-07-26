import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:signature/signature.dart';
import 'package:url_launcher/url_launcher.dart';
import 'api.dart';

void main() => runApp(const DriverApp());

class DriverApp extends StatefulWidget {
  const DriverApp({super.key});
  @override State<DriverApp> createState() => _DriverAppState();
}

class _DriverAppState extends State<DriverApp> {
  final api = CakeCityApi();
  bool checking = true, authenticated = false;
  @override void initState() { super.initState(); api.restore().then((ok) => setState(() { authenticated = ok; checking = false; })); }
  @override Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false, title: 'Cake City Driver',
    theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff67152f), surface: const Color(0xfffffbf7)), useMaterial3: true),
    home: checking ? const Scaffold(body: Center(child: CircularProgressIndicator())) :
      authenticated ? AssignmentList(api: api, logout: () async { await api.logout(); setState(() => authenticated = false); }) :
      Login(api: api, done: () => setState(() => authenticated = true)),
  );
}

class Login extends StatefulWidget {
  const Login({super.key, required this.api, required this.done});
  final CakeCityApi api; final VoidCallback done;
  @override State<Login> createState() => _LoginState();
}
class _LoginState extends State<Login> {
  final email = TextEditingController(), password = TextEditingController(); String error = '';
  @override Widget build(BuildContext context) => Scaffold(body: SafeArea(child: Center(child: ConstrainedBox(
    constraints: const BoxConstraints(maxWidth: 430), child: Padding(padding: const EdgeInsets.all(28), child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const Icon(Icons.delivery_dining, size: 62), const SizedBox(height: 18),
      Text('CAKE CITY', style: Theme.of(context).textTheme.labelLarge), Text('Deliver joy, beautifully.', style: Theme.of(context).textTheme.displaySmall),
      const SizedBox(height: 28), TextField(controller: email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Driver email')),
      const SizedBox(height: 12), TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
      if (error.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error, style: const TextStyle(color: Colors.red))),
      const SizedBox(height: 18), FilledButton(onPressed: () async { try { await widget.api.login(email.text.trim(), password.text); widget.done(); } catch (e) { setState(() => error = e.toString().replaceFirst('Exception: ', '')); } }, child: const Text('Start my route')),
    ]))),
  )));
}

class AssignmentList extends StatefulWidget {
  const AssignmentList({super.key, required this.api, required this.logout});
  final CakeCityApi api; final VoidCallback logout;
  @override State<AssignmentList> createState() => _AssignmentListState();
}
class _AssignmentListState extends State<AssignmentList> {
  List<dynamic> items = []; String error = '';
  Future<void> load() async { try { final value = await widget.api.request('/v1/driver/assignments'); setState(() { items = value; error = ''; }); } catch (e) { setState(() => error = '$e'); } }
  @override void initState() { super.initState(); load(); }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Today’s route'), actions: [IconButton(onPressed: widget.logout, icon: const Icon(Icons.logout))]), body: RefreshIndicator(onRefresh: load, child: ListView(padding: const EdgeInsets.all(18), children: [
    Text('${items.length} active deliveries', style: Theme.of(context).textTheme.headlineMedium),
    if (error.isNotEmpty) Text(error, style: const TextStyle(color: Colors.red)),
    ...items.map((item) => Card(child: ListTile(contentPadding: const EdgeInsets.all(18), leading: const CircleAvatar(child: Icon(Icons.cake)), title: Text(item['reference']), subtitle: Text('${item['customer_name']}\n${item['delivery_slot'] ?? 'Delivery time pending'}'), trailing: const Icon(Icons.arrow_forward), onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => Delivery(api: widget.api, assignment: item))).then((_) => load())))),
  ])));
}

class Delivery extends StatefulWidget {
  const Delivery({super.key, required this.api, required this.assignment});
  final CakeCityApi api; final Map<String, dynamic> assignment;
  @override State<Delivery> createState() => _DeliveryState();
}
class _DeliveryState extends State<Delivery> {
  Timer? timer; String status = ''; List<dynamic> messages = []; final message = TextEditingController();
  String get id => widget.assignment['id'];
  @override void initState() { super.initState(); loadMessages(); startLocation(); }
  @override void dispose() { timer?.cancel(); super.dispose(); }
  Future<void> startLocation() async {
    if (!await Geolocator.isLocationServiceEnabled()) return;
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
    if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) return;
    await sendLocation(); timer = Timer.periodic(const Duration(seconds: 20), (_) => sendLocation());
  }
  Future<void> sendLocation() async { try { final p = await Geolocator.getCurrentPosition(); await widget.api.request('/v1/driver/assignments/$id/location', method: 'POST', body: {'latitude': p.latitude, 'longitude': p.longitude, 'accuracy_meters': p.accuracy}); } catch (_) {} }
  Future<void> loadMessages() async { final value = await widget.api.request('/v1/driver/assignments/$id/messages'); if (mounted) setState(() => messages = value); }
  Future<void> action(String path) async { try { await widget.api.request('/v1/driver/assignments/$id/$path', method: 'POST', body: {}, headers: path == 'accept' ? null : {'Idempotency-Key': 'driver-$id-$path-${DateTime.now().millisecondsSinceEpoch}'}); setState(() => status = 'Update accepted and syncing with dispatch.'); } catch (e) { setState(() => status = '$e'); } }
  @override Widget build(BuildContext context) {
    final a = widget.assignment; final address = a['delivery_address'] ?? '';
    return Scaffold(appBar: AppBar(title: Text(a['reference'])), body: ListView(padding: const EdgeInsets.all(20), children: [
      Text(a['customer_name'], style: Theme.of(context).textTheme.headlineMedium), Text(address), const SizedBox(height: 16),
      Wrap(spacing: 10, children: [
        OutlinedButton.icon(onPressed: () => launchUrl(Uri.parse('tel:${a['customer_phone']}')), icon: const Icon(Icons.call), label: const Text('Call')),
        OutlinedButton.icon(onPressed: () => launchUrl(Uri.parse('https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(address)}'), mode: LaunchMode.externalApplication), icon: const Icon(Icons.navigation), label: const Text('Navigate')),
      ]),
      const SizedBox(height: 14),
      if (a['accepted_at'] == null) FilledButton(onPressed: () => action('accept'), child: const Text('Accept delivery')),
      if (a['state'] == 'driver_assigned') FilledButton(onPressed: () => action('pickup'), child: const Text('Cake collected — start delivery')),
      if (a['state'] == 'out_for_delivery') FilledButton.icon(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => Proof(api: widget.api, id: id))), icon: const Icon(Icons.verified), label: const Text('Complete proof of delivery')),
      if (status.isNotEmpty) Padding(padding: const EdgeInsets.all(10), child: Text(status)),
      const Divider(height: 38), Text('Customer chat', style: Theme.of(context).textTheme.titleLarge),
      ...messages.map((m) => ListTile(dense: true, title: Text(m['body']), subtitle: Text(m['sender_role']))),
      Row(children: [Expanded(child: TextField(controller: message, decoration: const InputDecoration(hintText: 'Write a message'))), IconButton(onPressed: () async { if (message.text.trim().isEmpty) return; await widget.api.request('/v1/driver/assignments/$id/messages', method: 'POST', body: {'body': message.text.trim()}); message.clear(); loadMessages(); }, icon: const Icon(Icons.send))]),
    ]));
  }
}

class Proof extends StatefulWidget {
  const Proof({super.key, required this.api, required this.id}); final CakeCityApi api; final String id;
  @override State<Proof> createState() => _ProofState();
}
class _ProofState extends State<Proof> {
  final otp = TextEditingController(), recipient = TextEditingController();
  final signature = SignatureController(penStrokeWidth: 3, penColor: const Color(0xff67152f), exportBackgroundColor: Colors.white);
  Uint8List? photo; String status = ''; bool busy = false;
  Future<void> submit() async {
    final signed = await signature.toPngBytes();
    if (photo == null || signed == null) { setState(() => status = 'Photo and signature are required.'); return; }
    setState(() => busy = true);
    try {
      final photoUrl = await widget.api.uploadProof(photo!), signatureUrl = await widget.api.uploadProof(signed);
      await widget.api.request('/v1/driver/assignments/${widget.id}/proof', method: 'POST', headers: {'Idempotency-Key': 'proof-${widget.id}-${DateTime.now().millisecondsSinceEpoch}'}, body: {'otp': otp.text, 'proof_photo_url': photoUrl, 'signature_url': signatureUrl, 'recipient_name': recipient.text});
      if (mounted) Navigator.pop(context);
    } catch (e) { setState(() { status = '$e'; busy = false; }); }
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Proof of delivery')), body: ListView(padding: const EdgeInsets.all(20), children: [
    TextField(controller: recipient, decoration: const InputDecoration(labelText: 'Recipient name')),
    TextField(controller: otp, keyboardType: TextInputType.number, maxLength: 6, decoration: const InputDecoration(labelText: 'Customer’s 6-digit delivery code')),
    const SizedBox(height: 10), OutlinedButton.icon(onPressed: () async { final image = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 75); if (image != null) { final bytes = await image.readAsBytes(); setState(() => photo = bytes); } }, icon: const Icon(Icons.camera_alt), label: Text(photo == null ? 'Take delivery photo' : 'Photo captured')),
    const SizedBox(height: 12), const Text('Recipient signature'), Container(height: 180, decoration: BoxDecoration(border: Border.all(color: Colors.grey)), child: Signature(controller: signature, backgroundColor: Colors.white)),
    TextButton(onPressed: signature.clear, child: const Text('Clear signature')), if (status.isNotEmpty) Text(status, style: const TextStyle(color: Colors.red)),
    FilledButton(onPressed: busy ? null : submit, child: Text(busy ? 'Uploading secure proof…' : 'Confirm delivery')),
  ]));
}
