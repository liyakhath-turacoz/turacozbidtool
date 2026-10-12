import 'dart:async';
import 'package:flutter/material.dart';
import 'api_client.dart';

class ProductSourcesPage extends StatefulWidget {
  const ProductSourcesPage({super.key, required this.token});
  final String token;
  @override
  State<ProductSourcesPage> createState() => _ProductSourcesPageState();
}

class _ProductSourcesPageState extends State<ProductSourcesPage> {
  final api = ApiClient();
  Map<String, dynamic> data = {}, stats = {};
  String? error;
  bool busy = false;
  Timer? timer;
  @override
  void initState() {
    super.initState();
    load();
    timer = Timer.periodic(const Duration(seconds: 5), (_) => load());
  }

  @override
  void dispose() {
    timer?.cancel();
    super.dispose();
  }

  Future<void> load() async {
    try {
      final result = await api.productSources(widget.token);
      final report = stats.isEmpty
          ? await api.productStatistics(widget.token)
          : stats;
      if (mounted)
        setState(() {
          data = result;
          stats = report;
        });
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  Future<void> fetchNow(String id) async {
    setState(() => busy = true);
    try {
      await api.fetchProductSource(widget.token, id);
      await load();
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> configure(Map<String, dynamic> source) async {
    final name = TextEditingController(text: source['name']);
    final endpoint = TextEditingController(text: source['endpoint']);
    final types = TextEditingController(
      text: (source['categories'] as List).join(', '),
    );
    final interval = TextEditingController(text: '${source['interval_hours']}');
    final atTime = TextEditingController(text: source['at_time']);
    final runAt = TextEditingController(text: source['run_at'] ?? '');
    final maximum = TextEditingController(text: '${source['max_products']}');
    var schedule = source['schedule_type'].toString();
    var enabled = source['enabled'] == true || source['enabled'] == 1;
    var zone = source['timezone'].toString();
    final availableTypes = List<String>.from(source['available_types'] ?? []);
    final selectedTypes = Set<String>.from(source['categories']);
    String? formError;
    bool saving = false;
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, change) => AlertDialog(
          title: Text('Configure ${source['name']}'),
          content: SizedBox(
            width: 560,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (formError != null)
                    Text(formError!, style: const TextStyle(color: Colors.red)),
                  TextField(
                    controller: name,
                    decoration: const InputDecoration(labelText: 'Source name'),
                  ),
                  TextField(
                    controller: endpoint,
                    decoration: const InputDecoration(labelText: 'Source URL'),
                  ),
                  DropdownButtonFormField<String>(
                    value: schedule,
                    decoration: const InputDecoration(labelText: 'Schedule'),
                    items: ['manual', 'hourly', 'daily', 'fixed']
                        .map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => change(() => schedule = value!),
                  ),
                  SwitchListTile(
                    title: const Text('Automatic imports enabled'),
                    value: enabled,
                    onChanged: (value) => change(() => enabled = value),
                  ),
                  if (schedule == 'hourly')
                    TextField(
                      controller: interval,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Interval (hours)',
                      ),
                    ),
                  if (schedule == 'daily')
                    TextField(
                      controller: atTime,
                      decoration: const InputDecoration(
                        labelText: 'Daily time (HH:MM)',
                      ),
                    ),
                  if (schedule == 'fixed')
                    TextField(
                      controller: runAt,
                      decoration: const InputDecoration(
                        labelText: 'Fixed date/time (YYYY-MM-DDTHH:MM)',
                      ),
                    ),
                  DropdownButtonFormField<String>(
                    value: zone,
                    decoration: const InputDecoration(labelText: 'Time zone'),
                    items: ['Asia/Kolkata', 'UTC']
                        .map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => change(() => zone = value!),
                  ),
                  TextField(
                    controller: maximum,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Products per run (1–2000)',
                    ),
                  ),
                  if (availableTypes.isEmpty)
                    TextField(
                      controller: types,
                      decoration: const InputDecoration(
                        labelText: 'Product types (comma separated)',
                      ),
                    ),
                  if (availableTypes.isNotEmpty)
                    Wrap(
                      spacing: 8,
                      children: [
                        for (final item in availableTypes)
                          FilterChip(
                            label: Text(item),
                            selected: selectedTypes.contains(item),
                            onSelected: (value) => change(() {
                              if (value) {
                                selectedTypes.add(item);
                              } else {
                                selectedTypes.remove(item);
                              }
                            }),
                          ),
                      ],
                    ),
                  const Text(
                    'Credentials stay in private server settings. Only released products with date evidence are imported.',
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      change(() => saving = true);
                      try {
                        final settings = <String, dynamic>{
                          'name': name.text.trim(),
                          'adapter': source['adapter'],
                          'endpoint': endpoint.text.trim(),
                          'schedule_type': schedule,
                          'enabled': enabled,
                          'interval_hours': int.tryParse(interval.text) ?? 1,
                          'at_time': atTime.text,
                          'run_at': runAt.text.isEmpty ? null : runAt.text,
                          'timezone': zone,
                          'max_products': int.tryParse(maximum.text) ?? 100,
                          'categories': availableTypes.isNotEmpty
                              ? selectedTypes.toList()
                              : types.text
                                    .split(',')
                                    .map((value) => value.trim())
                                    .where((value) => value.isNotEmpty)
                                    .toList(),
                        };
                        if (source['id'] == 'new') {
                          await api.createProductSource(widget.token, settings);
                        } else {
                          await api.saveProductSource(
                            widget.token,
                            source['id'],
                            settings,
                          );
                        }
                        if (ctx.mounted) Navigator.pop(ctx);
                        await load();
                      } catch (e) {
                        if (ctx.mounted) change(() => formError = e.toString());
                      } finally {
                        if (ctx.mounted) change(() => saving = false);
                      }
                    },
              child: Text(saving ? 'Saving…' : 'Save source settings'),
            ),
          ],
        ),
      ),
    );
    for (final controller in [
      name,
      endpoint,
      types,
      interval,
      atTime,
      runAt,
      maximum,
    ]) {
      controller.dispose();
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text(
        'Product Fetch & Reports',
        style: Theme.of(context).textTheme.headlineSmall,
      ),
      const Text(
        'Import released products within three years. Fetch now or set hourly, daily, or fixed schedules. Dates without release evidence are skipped.',
      ),
      Wrap(
        spacing: 8,
        children: [
          OutlinedButton(
            onPressed: () => configure({
              'id': 'new',
              'name': 'Custom product source',
              'adapter': 'json_feed',
              'endpoint': '',
              'categories': ['Smartphones'],
              'interval_hours': 1,
              'at_time': '09:00',
              'max_products': 100,
              'schedule_type': 'manual',
              'enabled': false,
              'timezone': 'Asia/Kolkata',
            }),
            child: const Text('Add JSON product source'),
          ),
          TextButton(
            onPressed: () {
              stats = {};
              load();
            },
            child: const Text('Refresh statistics'),
          ),
        ],
      ),
      if (error != null)
        Text(error!, style: const TextStyle(color: Colors.red)),
      for (final source in List<Map<String, dynamic>>.from(
        data['sources'] ?? [],
      ))
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  source['name'],
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Text(
                  '${source['schedule_type']} · ${source['timezone']} · ${source['max_products']} products/run',
                ),
                Text('Types: ${(source['categories'] as List).join(', ')}'),
                Text(source['structure']?.toString() ?? ''),
                Text(
                  'Next run: ${source['next_run_at'] == null ? 'Manual' : DateTime.parse('${source['next_run_at']}Z').toLocal()} (local time)',
                ),
                Wrap(
                  spacing: 8,
                  children: [
                    OutlinedButton(
                      onPressed: () => configure(source),
                      child: const Text('Configure source & schedule'),
                    ),
                    FilledButton(
                      onPressed: busy || source['credential_configured'] != true
                          ? null
                          : () => fetchNow(source['id']),
                      child: const Text('Fetch now'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      const Divider(),
      const Text(
        'Import history',
        style: TextStyle(fontWeight: FontWeight.bold),
      ),
      for (final job in List<Map<String, dynamic>>.from(data['jobs'] ?? []))
        ExpansionTile(
          title: Text('${job['source_name']} · ${job['status']}'),
          subtitle: Text(
            'New ${job['created_count']} · Updated ${job['updated_count']} · Skipped ${job['skipped_count']}\n${job['error_message'] ?? ''}',
          ),
          children: [
            SelectableText('${job['details']?['reasons'] ?? {}}'),
            for (final lead in List<Map<String, dynamic>>.from(
              job['details']?['leads'] ?? [],
            ))
              Padding(
                padding: const EdgeInsets.all(8),
                child: SelectableText('${lead['title']}\n${lead['url']}'),
              ),
          ],
        ),
      const Divider(),
      Text('${stats['total'] ?? 0} product records'),
      Text(
        '${stats['model_codes'] ?? 0} distinct brand/model codes; ${stats['unverified_legacy_years'] ?? 0} legacy records have unverified release years.',
      ),
      ExpansionTile(
        title: const Text('Year totals'),
        children: [
          for (final row in List<Map<String, dynamic>>.from(
            stats['years'] ?? [],
          ))
            ListTile(
              title: Text('${row['release_year'] ?? 'Unknown'}'),
              subtitle: Text('${row['model_codes']} distinct model codes'),
              trailing: Text('${row['count']}'),
            ),
        ],
      ),
      ExpansionTile(
        title: const Text('Brand totals'),
        children: [
          for (final row in List<Map<String, dynamic>>.from(
            stats['brands'] ?? [],
          ))
            ListTile(
              title: Text('${row['brand'] ?? 'Unknown'}'),
              trailing: Text('${row['count']}'),
            ),
        ],
      ),
      const Text(
        'Category / year breakdown',
        style: TextStyle(fontWeight: FontWeight.bold),
      ),
      for (final row in List<Map<String, dynamic>>.from(
        stats['category_years'] ?? [],
      ))
        ListTile(
          dense: true,
          title: Text(
            '${row['category']} / ${row['product_type']} · ${row['release_year'] ?? 'Unknown year'}',
          ),
          trailing: Text('${row['count']}'),
        ),
    ],
  );
}
