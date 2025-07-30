from datetime import datetime
from decimal import Decimal
import logging

PriceEntry_t = tuple[datetime, Decimal]

class Queue:
    def __init__(self):
        self.items = []

    def is_empty(self):
        return self.size() == 0

    def enqueue(self, item):
        self.items.insert(0, item)

    def dequeue(self):
        return self.items.pop()

    def size(self):
        return len(self.items)

def _search_date(pricelist: list[PriceEntry_t], date: datetime) \
    -> PriceEntry_t | None:
    if not len(pricelist):
        return None

    low = 0
    high = len(pricelist) - 1

    while (high > low):
        mid = (low + high) // 2
        mid_date = pricelist[mid][0]
        if mid_date > date:
            high = mid
        elif mid == low:
            high_date = pricelist[high][0]
            if high_date <= date:
                low = high
            else:
                high -= 1
        else:
            low = mid

    found = pricelist[low]
    if date >= found[0]:
        return found
    else:
        return None

class CommodityNode():

    def __init__(self, commodity):
        self._commodity = commodity
        self._adjacent: dict[str, list[PriceEntry_t]] = dict()
        self._sorted: dict[str, bool] = dict()

    def adjacent(self, commodity=None):
        if not commodity:
            return self._adjacent.keys()
        else:
            return commodity in self._adjacent

    def add_price(self, date: datetime, commodity: str, quantity: Decimal):
        if commodity in self._adjacent:
            self._adjacent[commodity].append((date, quantity))
            self._sorted[commodity] = False
        else:
            self._adjacent[commodity] = [(date, quantity)]
            self._sorted[commodity] = True

    def _sort(self, commodity):
        if self._sorted[commodity]: return
        # Sort in ascending order of dates.
        self._adjacent.commodity.sort(key=lambda x: x[0])
        self._sorted[commodity] = True

    def get_price(self, date: datetime, commodity: str) -> PriceEntry_t | None:
        if commodity not in self._adjacent:
            return None
        self._sort(commodity)
        return _search_date(self._adjacent[commodity], date)

class Exchange():

    def __init__(self):
        self._commodities: dict[str, CommodityNode] = dict()
        self._sorted: bool = True

    def add_price(self, date: datetime, src_cmdty: str,
                  dst_cmdty: str, quantity: Decimal):
        self._add_price(date, src_cmdty, dst_cmdty, quantity)
        self._add_price(date, dst_cmdty, src_cmdty, 1/quantity)

    def _add_price(self, date: datetime, src_cmdty: str,
                   dst_cmdty: str, quantity: Decimal):
        if src_cmdty not in self._commodities:
            self._commodities[src_cmdty] = CommodityNode(src_cmdty)
        self._commodities[src_cmdty].add_price(date, dst_cmdty, quantity)

    def get_price(self, date: datetime, src_cmdty: str, dst_cmdty: str) \
        -> Decimal | None:
        if not (src_cmdty or dst_cmdty):
            return None
        if src_cmdty not in self._commodities:
            return None
        visited = set()
        queue = Queue()

        # The path starts with itself with a conversion factor of 1.
        start = (src_cmdty, date, 1)
        queue.enqueue([start])
        # A path looks like:
        # [(commodity, date, factor),
        #  (commodity, date, factor),
        #  ...]
        #
        # If a path is found, this variable is assigned to it.
        found = None

        debug = False

        while queue.size():
            path = queue.dequeue()
            cmdty = path[-1][0]
            if debug:
                print(f"Visiting {cmdty}")
            if cmdty == dst_cmdty:
                found = path
                break
            visited.add(cmdty)
            node = self._commodities[cmdty]
            for i in node.adjacent():
                if i in visited: continue
                p = node.get_price(date, i)
                if not p: continue
                new_path = path.copy()
                new_path.append((i, p[0], p[1]))
                queue.enqueue(new_path)

        if debug:
            print(f"Found {found}")

        if found:
            x = 1
            for i in found:
                x *= i[2]
            return x
