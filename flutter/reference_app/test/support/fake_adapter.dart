import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

typedef FakeHandler = Future<ResponseBody> Function(RequestOptions options);

/// A scripted [HttpClientAdapter]: the real Dio pipeline (interceptors, error
/// handling, JSON decoding) runs; only the network is replaced.
///
/// Two modes: a FIFO queue ([enqueue]) for ordered scenarios like retries, or
/// [routes] by path for screens that fire several requests concurrently.
class FakeAdapter implements HttpClientAdapter {
  FakeAdapter({this.routes = const {}});

  final Map<String, FakeHandler> routes;
  final List<FakeHandler> _queue = [];
  final List<RequestOptions> requests = [];

  void enqueue(FakeHandler handler) => _queue.add(handler);

  void enqueueJson(Object? body, {int status = 200, Map<String, String> headers = const {}}) =>
      enqueue((_) async => jsonResponse(body, status: status, headers: headers));

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    requests.add(options);
    final route = routes[options.uri.path];
    if (route != null) return route(options);
    if (_queue.isEmpty) throw StateError('Unexpected request: ${options.method} ${options.uri}');
    return _queue.removeAt(0)(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody jsonResponse(
  Object? body, {
  int status = 200,
  String contentType = 'application/json',
  Map<String, String> headers = const {},
}) => ResponseBody.fromString(
  jsonEncode(body),
  status,
  headers: {
    Headers.contentTypeHeader: [contentType],
    for (final MapEntry(:key, :value) in headers.entries) key: [value],
  },
);

ResponseBody problemResponse(int status, String code, {Map<String, Object?> extra = const {}}) =>
    jsonResponse(
      {
        'type': 'https://errors.reference.dev/$code',
        'title': 'T',
        'status': status,
        'code': code,
        'request_id': 'srv-1',
        ...extra,
      },
      status: status,
      contentType: 'application/problem+json',
    );
