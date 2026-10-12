import 'package:flutter/material.dart';

Map<String, dynamic> emptyCatalogFilters() => {
  'categories': <String>[],
  'product_types': <String>[],
  'brands': <String>[],
  'years': <String>[],
  'specs': <String, dynamic>{},
  'sort': 'Newest',
  'minimum': '',
  'maximum': '',
};

class CatalogFacetPicker extends StatelessWidget {
  const CatalogFacetPicker({
    super.key,
    required this.facets,
    required this.filters,
    required this.onChanged,
    this.specsOnly = false,
  });
  final Map<String, dynamic> facets, filters;
  final ValueChanged<Map<String, dynamic>> onChanged;
  final bool specsOnly;
  void toggle(String key, String value) {
    final selected = List<String>.from(filters[key] ?? []);
    selected.contains(value) ? selected.remove(value) : selected.add(value);
    onChanged({...filters, key: selected});
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      if (!specsOnly)
        for (final entry in {
          'categories': 'Categories',
          'product_types': 'Product type',
          'brands': 'Brand / manufacturer',
        }.entries)
          FacetChoices(
            label: entry.value,
            rows: List<Map<String, dynamic>>.from(facets[entry.key] ?? []),
            selected: List<String>.from(filters[entry.key] ?? []),
            onToggle: (value) => toggle(entry.key, value),
          ),
      FacetChoices(
        label: 'Release year',
        rows: List<Map<String, dynamic>>.from(facets['years'] ?? []),
        selected: List<String>.from(filters['years'] ?? []),
        onToggle: (value) => toggle('years', value),
      ),
      for (final facet in List<Map<String, dynamic>>.from(
        facets['specifications'] ?? [],
      ))
        FacetChoices(
          label: facet['label'].toString(),
          rows: List<Map<String, dynamic>>.from(facet['values'] ?? []),
          selected: List<String>.from(
            (filters['specs'] ?? {})[facet['key']] ?? [],
          ),
          onToggle: (value) {
            final specs = Map<String, dynamic>.from(filters['specs'] ?? {});
            final values = List<String>.from(specs[facet['key']] ?? []);
            values.contains(value) ? values.remove(value) : values.add(value);
            if (values.isEmpty) {
              specs.remove(facet['key']);
            } else {
              specs[facet['key']] = values;
            }
            onChanged({...filters, 'specs': specs});
          },
        ),
    ],
  );
}

class FacetChoices extends StatefulWidget {
  const FacetChoices({
    super.key,
    required this.label,
    required this.rows,
    required this.selected,
    required this.onToggle,
  });
  final String label;
  final List<Map<String, dynamic>> rows;
  final List<String> selected;
  final ValueChanged<String> onToggle;
  @override
  State<FacetChoices> createState() => _FacetChoicesState();
}

class _FacetChoicesState extends State<FacetChoices> {
  String search = '';
  bool expanded = false;
  @override
  Widget build(BuildContext context) {
    final rows = widget.rows
        .where(
          (row) => row['value'].toString().toLowerCase().contains(
            search.toLowerCase(),
          ),
        )
        .toList();
    return ExpansionTile(
      key: PageStorageKey(widget.label),
      initiallyExpanded: [
        'Categories',
        'Product type',
        'Release year',
      ].contains(widget.label),
      title: Text(
        '${widget.label}${widget.selected.isEmpty ? '' : ' (${widget.selected.length})'}',
      ),
      children: [
        if (widget.rows.length > 12)
          TextField(
            decoration: InputDecoration(
              labelText: 'Find ${widget.label.toLowerCase()}',
            ),
            onChanged: (value) => setState(() => search = value),
          ),
        for (final row in rows.take(expanded ? rows.length : 25))
          CheckboxListTile(
            dense: true,
            title: Text(
              row['value'] == 'unknown'
                  ? 'Year not supplied'
                  : row['value'].toString(),
            ),
            subtitle: Text('${row['count']} products'),
            value: widget.selected.contains(row['value'].toString()),
            onChanged: (_) => widget.onToggle(row['value'].toString()),
          ),
        if (rows.length > 25)
          TextButton(
            onPressed: () => setState(() => expanded = !expanded),
            child: Text(expanded ? 'Show fewer' : 'Show all values'),
          ),
      ],
    );
  }
}
