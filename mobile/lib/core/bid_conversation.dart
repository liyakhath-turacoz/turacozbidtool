import 'package:flutter/material.dart';
import 'api_client.dart';
import 'models.dart';

final liveBidRecords = ValueNotifier<List<BidRecord>>([]);
final bidChatReconnects = ValueNotifier<int>(0);
final liveBidMessages = ValueNotifier<Map<String, List<Map<String, dynamic>>>>(
  {},
);
SessionUser? bidChatSession;

List<Map<String, dynamic>> mergeBidMessages(
  List<Map<String, dynamic>> first,
  List<Map<String, dynamic>> second,
) {
  final items = {
    for (final item in [...first, ...second]) item['id'].toString(): item,
  };
  return items.values.toList()
    ..sort((a, b) => '${a['created_at']}'.compareTo('${b['created_at']}'));
}

void receiveBidMessage(String bidId, Map<String, dynamic> message) {
  liveBidMessages.value = {
    ...liveBidMessages.value,
    bidId: mergeBidMessages(liveBidMessages.value[bidId] ?? [], [message]),
  };
}

class BidConversation extends StatefulWidget {
  const BidConversation({super.key, required this.bidId, required this.user});
  final String bidId;
  final SessionUser user;
  @override
  State<BidConversation> createState() => _BidConversationState();
}

class _BidConversationState extends State<BidConversation> {
  final _draft = TextEditingController();
  List<Map<String, dynamic>> _messages = [];
  bool _sending = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    if (widget.user.role != UserRole.admin) return;
    bidChatReconnects.addListener(_load);
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await ApiClient().bidMessages(
        widget.user.accessToken,
        widget.bidId,
      );
      if (mounted)
        setState(() => _messages = mergeBidMessages(_messages, rows));
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  Future<void> _send() async {
    final text = _draft.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      final sent = await ApiClient().sendBidMessage(
        widget.user.accessToken,
        widget.bidId,
        text,
      );
      if (mounted)
        setState(() {
          _messages = mergeBidMessages(_messages, [sent]);
          _draft.clear();
        });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  void dispose() {
    bidChatReconnects.removeListener(_load);
    _draft.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.user.role != UserRole.admin
      ? const SizedBox.shrink()
      : ValueListenableBuilder<Map<String, List<Map<String, dynamic>>>>(
          valueListenable: liveBidMessages,
          builder: (context, updates, _) {
            final messages = mergeBidMessages(
              _messages,
              updates[widget.bidId] ?? [],
            );
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Divider(),
                const Text(
                  'Private bid conversation',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                if (messages.isEmpty) const Text('No messages yet.'),
                for (final message in messages)
                  ListTile(
                    dense: true,
                    title: Text(message['message'].toString()),
                    subtitle: Text(
                      '${message['sender_name']} · ${message['created_at']}',
                    ),
                  ),
                if (_error != null)
                  Text(_error!, style: const TextStyle(color: Colors.red)),
                if (widget.user.role != UserRole.admin)
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _draft,
                          maxLength: 4000,
                          decoration: const InputDecoration(
                            labelText: 'Bid message',
                          ),
                          onSubmitted: (_) => _send(),
                        ),
                      ),
                      IconButton(
                        tooltip: 'Send bid message',
                        onPressed: _sending ? null : _send,
                        icon: const Icon(Icons.send),
                      ),
                    ],
                  ),
              ],
            );
          },
        );
}

void showLiveBidDialog(
  BuildContext context,
  BidRecord initial, {
  bool isMine = false,
}) {
  final user = bidChatSession;
  showDialog<void>(
    context: context,
    builder: (dialogContext) => ValueListenableBuilder<List<BidRecord>>(
      valueListenable: liveBidRecords,
      builder: (context, records, _) {
        final bid =
            records.where((row) => row.id == initial.id).firstOrNull ?? initial;
        final winner = bid.status == 'won' || bid.status == 'completed';
        final participant = user?.role == UserRole.buyer || (isMine && winner);
        return AlertDialog(
          title: Text(bid.product),
          content: SizedBox(
            width: 520,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Request ${bid.bidRequestId}'),
                  Text('Status: ${bid.status}'),
                  Text('Offer: Rs. ${bid.amount.toStringAsFixed(2)}'),
                  Text('Warranty: ${bid.warrantyText}'),
                  Text('Delivery: ${bid.deliveryTime}'),
                  Text(bid.notes),
                  Text(bid.freeGifts),
                  Text(bid.extraServices),
                  const Divider(),
                  const Text('All offers for this request'),
                  for (final offer in records.where(
                    (row) =>
                        row.bidRequestId == bid.bidRequestId &&
                        row.status != 'withdrawn',
                  ))
                    Text(
                      '${offer.dealer}: Rs. ${offer.amount.toStringAsFixed(2)} (${offer.status})',
                    ),
                  if (winner && participant) ...[
                    const Divider(),
                    const Text('Contact details'),
                    if (user?.role == UserRole.dealer) ...[
                      Text(bid.buyer),
                      Text(bid.buyerPhone),
                      Text(bid.buyerEmail),
                      Text(bid.buyerAddress),
                    ] else ...[
                      Text(bid.dealer),
                      Text(bid.ownerName),
                      Text(bid.dealerPhone),
                      Text(bid.dealerEmail),
                      Text(bid.businessAddress),
                    ],
                  ],
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Close'),
            ),
          ],
        );
      },
    ),
  );
}
