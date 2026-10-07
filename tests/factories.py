######################################################################
# Test Factory to make fake objects for testing
######################################################################
"""
Test Factory to make fake Shopcart and Item objects for testing
"""

from factory import Factory, SubFactory, Sequence, Faker, post_generation
from factory.fuzzy import FuzzyDecimal, FuzzyInteger
from service.models import Shopcart, Item


class ShopcartFactory(Factory):
    """Creates fake Shopcarts"""

    # pylint: disable=too-few-public-methods
    class Meta:
        """Persistent class"""

        model = Shopcart

    # customer_id must be unique, so use a Sequence instead of a random number
    customer_id = Sequence(lambda n: n + 1)

    @post_generation
    def items(
        self, create, extracted, **kwargs
    ):  # pylint: disable=method-hidden, unused-argument
        """Creates the items list"""
        if not create:
            return

        if extracted:
            self.items = extracted


class ItemFactory(Factory):
    """Creates fake Items"""

    # pylint: disable=too-few-public-methods
    class Meta:
        """Persistent class"""

        model = Item

    id = Sequence(lambda n: n)
    shopcart_id = None
    product_id = Sequence(lambda n: n + 100)
    name = Faker("word")
    description = Faker("sentence", nb_words=6)
    price = FuzzyDecimal(0.50, 999.99, 2)
    quantity = FuzzyInteger(1, 10)
    shopcart = SubFactory(ShopcartFactory)
