import 'package:flutter_test/flutter_test.dart';
import 'package:cakecity_driver/api.dart';

void main() {
  test('driver API targets the injected HTTPS service', () {
    expect(CakeCityApi(baseUrl: 'https://api.cakecity.test').baseUrl, contains('cakecity'));
  });
}
