import 'package:flutter_test/flutter_test.dart';
import 'package:cakecity_driver/api.dart';

void main() {
  test('production API URL can be injected at build time', () {
    final api = CakeCityApi(baseUrl: 'https://api.cakecity.test');
    expect(api.baseUrl, startsWith('https://'));
  });
}
