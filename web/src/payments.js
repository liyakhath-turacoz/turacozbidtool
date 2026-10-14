/* Opening the Razorpay payment window. Everything else about a payment happens on the server. */

let loading = null;

export function loadRazorpay() {
  if (typeof window !== 'undefined' && window.Razorpay) return Promise.resolve();
  if (!loading) {
    loading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = resolve;
      script.onerror = () => {
        loading = null;
        script.remove();
        reject(new Error('The payment window could not be loaded. Check your connection and try again.'));
      };
      document.head.appendChild(script);
    });
  }
  return loading;
}

/** Resolves with the proof Razorpay returns, or rejects with `cancelled: true` if the person closes the window. */
export function openRazorpay(order) {
  return new Promise((resolve, reject) => {
    const checkout = new window.Razorpay({
      key: order.key_id,
      amount: order.amount_paise,
      currency: order.currency,
      name: order.name,
      description: order.description,
      order_id: order.order_id,
      prefill: order.prefill,
      theme: { color: '#1F3AB4' },
      handler: (response) => resolve({
        order_id: response.razorpay_order_id,
        payment_id: response.razorpay_payment_id,
        signature: response.razorpay_signature,
      }),
      modal: { ondismiss: () => reject(Object.assign(new Error('Payment cancelled'), { cancelled: true })) },
    });
    checkout.on('payment.failed', (response) => reject(new Error(response?.error?.description || 'The payment did not go through.')));
    checkout.open();
  });
}
