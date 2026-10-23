import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import 'models.dart';
import 'api_client.dart' show apiBaseUrl;

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            color: Theme.of(
              context,
            ).colorScheme.primary.withValues(alpha: 0.12),
          ),
          child: Icon(icon, color: Theme.of(context).colorScheme.primary),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
              ),
              Text(subtitle),
            ],
          ),
        ),
        if (trailing != null) trailing!,
      ],
    );
  }
}

class MetricCard extends StatelessWidget {
  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.onTap,
  });

  final String label;
  final String value;
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 10),
              Text(
                value,
                style: Theme.of(
                  context,
                ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w900),
              ),
              Text(label, overflow: TextOverflow.ellipsis),
            ],
          ),
        ),
      ),
    );
  }
}

class ResponsiveMetricGrid extends StatelessWidget {
  const ResponsiveMetricGrid({super.key, required this.metrics});

  final List<Widget> metrics;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 1100
            ? 5
            : constraints.maxWidth >= 820
            ? 4
            : constraints.maxWidth >= 560
            ? 2
            : 1;
        return GridView.count(
          crossAxisCount: columns,
          childAspectRatio: 1.75,
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          children: metrics,
        );
      },
    );
  }
}

class DataPanel extends StatelessWidget {
  const DataPanel({
    super.key,
    required this.title,
    required this.children,
    this.action,
  });

  final String title;
  final List<Widget> children;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                ),
                if (action != null) action!,
              ],
            ),
            const SizedBox(height: 10),
            ...children,
          ],
        ),
      ),
    );
  }
}

class InfoChip extends StatelessWidget {
  const InfoChip(this.label, this.value, {super.key});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
      decoration: BoxDecoration(
        color: Theme.of(
          context,
        ).colorScheme.surfaceContainerHighest.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text('$label: $value'),
    );
  }
}

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final lower = text.toLowerCase();
    final color = lower.contains('ban') || lower.contains('fail')
        ? Colors.red
        : lower.contains('held') ||
              lower.contains('pending') ||
              lower.contains('flag')
        ? Colors.orange
        : Theme.of(context).colorScheme.primary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w800,
          fontSize: 12,
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 10),
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 6),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

class WarningBanner extends StatelessWidget {
  const WarningBanner({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final message = switch (status) {
      'held' =>
        'Your account is held. Bidding is blocked until admin releases the hold.',
      'suspended' => 'Your account is suspended. Access is restricted.',
      'banned' => 'Your account is banned. Participation is blocked.',
      'flagged' =>
        'Your account is flagged. You can continue, but admin review is active.',
      _ => 'Account status requires attention.',
    };
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber),
      ),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_outlined),
          const SizedBox(width: 8),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }
}

class ProductCard extends StatelessWidget {
  const ProductCard({
    super.key,
    required this.product,
    this.onCart,
    this.onBid,
    this.onSelect,
    this.selected = false,
  });

  final ProductItem product;
  final VoidCallback? onCart;
  final VoidCallback? onBid;
  final VoidCallback? onSelect;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final purple = Theme.of(context).colorScheme.primary;
    const green = Color(0xFF16A34A);
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
      clipBehavior: Clip.antiAlias,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: InkWell(
        onTap: onSelect,
        child: DecoratedBox(
          decoration: BoxDecoration(
            border: selected ? Border.all(color: purple, width: 2) : null,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  height: 110,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5F3FF),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: product.imageUrl.isNotEmpty
                      ? Image.network(
                          product.imageUrl.startsWith('/catalog-images/')
                              ? '$apiBaseUrl${product.imageUrl}'
                              : product.imageUrl,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => Icon(
                            Icons.inventory_2_outlined,
                            size: 40,
                            color: purple,
                          ),
                        )
                      : Center(
                          child: Icon(
                            Icons.inventory_2_outlined,
                            size: 40,
                            color: purple,
                          ),
                        ),
                ),
                const SizedBox(height: 8),
                Text(
                  product.brand.toUpperCase(),
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 10,
                    color: purple,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  product.name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  product.specifications.isEmpty
                      ? "Standard Edition"
                      : product.specifications.entries
                          .map((e) => "${e.key}: ${e.value}")
                          .take(2)
                          .join(" | "),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 11,
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  product.source == 'icecat'
                      ? '${product.releaseYear ?? 'Current'} model - Bid for price'
                      : '${money(product.priceMin)} - ${money(product.priceMax)}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w900,
                    fontSize: 14,
                    color: green,
                  ),
                ),
                const Spacer(),
                Row(
                  children: [
                    Expanded(
                      child: SizedBox(
                        height: 34,
                        child: FilledButton.icon(
                          onPressed: onCart,
                          style: FilledButton.styleFrom(
                            backgroundColor: green,
                            padding: EdgeInsets.zero,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                          icon: const Icon(Icons.add_shopping_cart, size: 14),
                          label: const Text('Add', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: SizedBox(
                        height: 34,
                        child: FilledButton.tonalIcon(
                          onPressed: onBid,
                          style: FilledButton.styleFrom(
                            padding: EdgeInsets.zero,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                          icon: const Icon(Icons.bolt, size: 14),
                          label: const Text('Bid', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class LocationMapPanel extends StatelessWidget {
  const LocationMapPanel({
    super.key,
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  static const points = [
    MapEntry('Andheri East', LatLng(19.1155, 72.8727)),
    MapEntry('Powai', LatLng(19.1176, 72.9060)),
    MapEntry('Bandra West', LatLng(19.0596, 72.8295)),
    MapEntry('Lower Parel', LatLng(18.9959, 72.8305)),
    MapEntry('Navi Mumbai', LatLng(19.0330, 73.0297)),
  ];

  @override
  Widget build(BuildContext context) {
    return DataPanel(
      title: title,
      children: [
        Text(subtitle),
        const SizedBox(height: 10),
        SizedBox(
          height: 250,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: FlutterMap(
              options: const MapOptions(
                initialCenter: LatLng(19.0760, 72.8777),
                initialZoom: 10.7,
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.turacoz.bidtool',
                ),
                CircleLayer(
                  circles: points
                      .map(
                        (entry) => CircleMarker(
                          point: entry.value,
                          radius: 7000,
                          useRadiusInMeter: true,
                          color: Theme.of(
                            context,
                          ).colorScheme.primary.withValues(alpha: 0.10),
                          borderColor: Theme.of(context).colorScheme.primary,
                          borderStrokeWidth: 1.5,
                        ),
                      )
                      .toList(),
                ),
                MarkerLayer(
                  markers: points
                      .map(
                        (entry) => Marker(
                          point: entry.value,
                          width: 120,
                          height: 44,
                          child: Column(
                            children: [
                              Icon(
                                Icons.location_pin,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                              Expanded(
                                child: FittedBox(
                                  child: Text(
                                    entry.key,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      )
                      .toList(),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
