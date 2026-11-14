from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Round

from apps.catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on delivery"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    STATUS_TRANSITIONS = {
        Status.PENDING: frozenset({Status.PENDING, Status.PROCESSING, Status.CANCELLED}),
        Status.PROCESSING: frozenset({Status.PROCESSING, Status.SHIPPED, Status.CANCELLED}),
        Status.SHIPPED: frozenset({Status.SHIPPED, Status.DELIVERED}),
        Status.DELIVERED: frozenset({Status.DELIVERED}),
        Status.CANCELLED: frozenset({Status.CANCELLED}),
    }
    PAYMENT_STATUS_TRANSITIONS = {
        PaymentStatus.PENDING: frozenset({PaymentStatus.PENDING, PaymentStatus.PAID, PaymentStatus.FAILED}),
        PaymentStatus.FAILED: frozenset({PaymentStatus.FAILED, PaymentStatus.PENDING}),
        PaymentStatus.PAID: frozenset({PaymentStatus.PAID, PaymentStatus.REFUNDED}),
        PaymentStatus.REFUNDED: frozenset({PaymentStatus.REFUNDED}),
    }

    order_number = models.CharField(max_length=24, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    shipping_name = models.CharField(max_length=200)
    shipping_email = models.EmailField()
    shipping_phone = models.CharField(max_length=30, blank=True)
    shipping_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "-created_at")), models.Index(fields=("status", "-created_at"))]
        constraints = [
            models.CheckConstraint(condition=models.Q(subtotal__gte=0), name="order_subtotal_nonnegative"),
            models.CheckConstraint(condition=models.Q(shipping_fee__gte=0), name="order_shipping_nonnegative"),
            models.CheckConstraint(condition=models.Q(total__gte=0), name="order_total_nonnegative"),
            models.CheckConstraint(
                condition=models.Q(total=models.F("subtotal") + models.F("shipping_fee")),
                name="order_total_matches_components",
            ),
        ]

    @classmethod
    def is_valid_status_transition(cls, current, new):
        return new in cls.STATUS_TRANSITIONS.get(current, ())

    @classmethod
    def is_valid_payment_transition(cls, current, new):
        return new in cls.PAYMENT_STATUS_TRANSITIONS.get(current, ())

    def clean(self):
        super().clean()
        if (
            self.total is not None
            and self.subtotal is not None
            and self.shipping_fee is not None
            and self.total != self.subtotal + self.shipping_fee
        ):
            raise ValidationError({"total": "Total must equal subtotal plus shipping."})
        if self.status == self.Status.CANCELLED and self.payment_status == self.PaymentStatus.PAID:
            raise ValidationError({"payment_status": "Paid orders cannot be cancelled."})

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=80)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_item_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="order_item_price_nonnegative"),
            models.CheckConstraint(condition=models.Q(line_total__gte=0), name="order_item_total_nonnegative"),
            models.CheckConstraint(
                condition=models.Q(
                    line_total=Round(models.F("unit_price") * models.F("quantity"), 2)
                ),
                name="order_item_line_total_matches",
            ),
        ]

    def clean(self):
        super().clean()
        if self.unit_price is not None and self.quantity and self.line_total is not None:
            expected_total = (self.unit_price * self.quantity).quantize(Decimal("0.01"))
            if self.line_total != expected_total:
                raise ValidationError({"line_total": "Line total must equal unit price multiplied by quantity."})
