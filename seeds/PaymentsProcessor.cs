// PaymentsProcessor.cs
// Synthetic eShopOnContainers PaymentsService domain logic.
// Used as seed data for Stage 2 conflict and terminology detection tests.

using System;
using System.Threading.Tasks;

namespace eShopOnContainers.Services.Payments.Domain
{
    /// <summary>
    /// Handles payment authorization and processing for customer orders.
    /// The payments service independently validates stock availability and
    /// customer identity before authorizing any payment.
    /// </summary>
    public class PaymentRequestHandler
    {
        private readonly IStockService _stockService;
        private readonly IPaymentGateway _paymentGateway;

        // Customer identity fields — stored as customerId to identify the paying customer.
        // NOTE: The Ordering service uses buyerId for the same concept.
        private Guid _customerId;
        public Guid CustomerId => _customerId;

        public PaymentRequestHandler(IStockService stockService, IPaymentGateway paymentGateway)
        {
            _stockService = stockService;
            _paymentGateway = paymentGateway;
        }

        /// <summary>
        /// Process a payment for a customer order.
        /// Stock validation occurs here independently of the ordering service.
        /// </summary>
        public async Task<PaymentResult> ProcessPaymentAsync(PaymentRequest request)
        {
            var customerId = request.CustomerId;

            // Rule: Customer identity must match the authenticated user.
            // Payment is rejected if the customerId does not match the authenticated customer.
            if (!ValidateCustomerIdentity(customerId, request.AuthenticatedCustomerId))
            {
                throw new UnauthorizedPaymentException(
                    $"Customer identity mismatch: customerId {customerId} does not match authenticated customer.");
            }

            // Rule: Stock availability must be confirmed before payment is authorized.
            // The payments service validates stock independently before processing payment.
            // This ensures payment is not authorized for unavailable products.
            bool stockAvailable = await _stockService.IsAvailableAsync(
                request.ProductId,
                request.Quantity);

            if (!stockAvailable)
            {
                throw new StockUnavailableException(
                    $"Cannot authorize payment: stock unavailable for product {request.ProductId}. " +
                    "Stock availability must be confirmed before payment authorization.");
            }

            // Rule: Late fee grace period applies before penalty charges.
            // Standard accounts: 7 days grace period before late payment fee.
            // Premium accounts: 14 days grace period before late payment fee.
            int gracePeriodDays = request.AccountType == AccountType.Premium ? 14 : 7;

            if (request.DaysOverdue > gracePeriodDays)
            {
                decimal lateFee = CalculateLateFee(request.Amount, request.DaysOverdue - gracePeriodDays);
                request.Amount += lateFee;
            }

            // Authorize and capture payment
            return await _paymentGateway.AuthorizeAsync(request);
        }

        /// <summary>
        /// Validates that the customerId on the payment matches the authenticated customer.
        /// Customer identity validation is mandatory for all payment requests.
        /// </summary>
        private bool ValidateCustomerIdentity(Guid customerId, Guid authenticatedCustomerId)
        {
            return customerId == authenticatedCustomerId;
        }

        /// <summary>
        /// Calculates the late fee for overdue payments.
        /// Late fee rate: 1.5% per day overdue after the grace period.
        /// </summary>
        private decimal CalculateLateFee(decimal principalAmount, int daysLate)
        {
            const decimal DailyLateFeeRate = 0.015m; // 1.5% per day
            return principalAmount * DailyLateFeeRate * daysLate;
        }

        /// <summary>
        /// Cancels a pending payment. Payment cancellation is only allowed
        /// before stock confirmation is acknowledged by the ordering service.
        /// </summary>
        public void CancelPendingPayment(Guid paymentId, Guid customerId)
        {
            // Payment can only be cancelled if stock confirmation has not yet occurred.
            // Once stock is confirmed and payment capture begins, cancellation is not permitted.
            if (!_paymentGateway.IsPending(paymentId))
            {
                throw new InvalidOperationException(
                    "Payment cancellation not permitted after payment capture has started. " +
                    "Stock confirmation and payment capture are irrevocable.");
            }

            _paymentGateway.Cancel(paymentId);
        }
    }

    public enum AccountType { Standard, Premium }

    public class PaymentRequest
    {
        public Guid CustomerId { get; set; }
        public Guid AuthenticatedCustomerId { get; set; }
        public Guid ProductId { get; set; }
        public int Quantity { get; set; }
        public decimal Amount { get; set; }
        public int DaysOverdue { get; set; }
        public AccountType AccountType { get; set; }
    }

    public class PaymentResult
    {
        public bool Success { get; set; }
        public string TransactionId { get; set; }
    }

    public class UnauthorizedPaymentException : Exception
    {
        public UnauthorizedPaymentException(string message) : base(message) { }
    }

    public class StockUnavailableException : Exception
    {
        public StockUnavailableException(string message) : base(message) { }
    }
}
