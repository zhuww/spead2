# Copyright 2015 SKA South Africa
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Send SPEAD protocol"""

from __future__ import print_function, division
import spead2 as _spead2
import weakref
from spead2._send import StreamConfig, BytesStream, UdpStream, Heap, PacketGenerator


class _ItemInfo(object):
    def __init__(self, item):
        self.version = None
        self.descriptor_cnt = None
        self.item = weakref.ref(item)


class HeapGenerator(object):
    """Tracks which items and item values have previously been sent and
    generates delta heaps.

    Parameters
    ----------
    item_group : :py:class:`spead2.ItemGroup`
        Item group to monitor.
    descriptor_frequency : int, optional
        If specified, descriptors will be re-sent once every `descriptor_frequency` heaps
        generated by this method.
    flavour : :py:class:`spead2.Flavour`
        The SPEAD protocol flavour used for heaps generated by :py:meth:`get_heap` and
        :py:meth:`get_end`.
    """
    def __init__(self, item_group, descriptor_frequency=None, flavour=_spead2.Flavour()):
        self._item_group = item_group
        self._info = {}              # Maps ID to _ItemInfo
        self._descriptor_frequency = descriptor_frequency
        # Counter for calls to add_to_heap. This is independent of the
        # protocol-level heap count.
        self._descriptor_cnt = 0
        self._flavour = flavour

    def _get_info(self, item):
        if item.id not in self._info:
            self._info[item.id] = _ItemInfo(item)
        return self._info[item.id]

    def _descriptor_stale(self, item, info):
        if info.descriptor_cnt is None:
            # Never been sent before
            return True
        if self._descriptor_frequency is not None \
                and self._descriptor_cnt - info.descriptor_cnt >= self._descriptor_frequency:
            # This descriptor is due for a resend
            return True
        # Check for complete replacement of the item
        orig_item = info.item()
        if orig_item is not item:
            info.version = None
            info.item = weakref.ref(item)
            return True
        return False

    def add_to_heap(self, heap, descriptors='stale', data='stale'):
        """Update a heap to contains all the new items and item descriptors
        since the last call.

        Parameters
        ----------
        heap : :py:class:`Heap`
            The heap to update.
        descriptors : {'stale', 'all', 'none'}
            Which descriptors to send. The default ('stale') sends only
            descriptors that have not been sent, or have not been sent recently
            enough according to the `descriptor_frequency` passed to the
            constructor. The other options are to send all the descriptors or
            none of them. Sending all descriptors is useful if a new receiver
            is added which will be out of date.
        data : {'stale', 'all', 'none'}
            Which data items to send.
        item_group : :py:class:`ItemGroup`, optional
            If specified, uses the items from this item group instead of the
            one passed to the constructor (which could be `None`).

        Raises
        ------
        ValueError
            if `descriptors` or `data` is not one of the legal values
        """
        if descriptors not in ['stale', 'all', 'none']:
            raise ValueError("descriptors must be one of 'stale', 'all', 'none'")
        if data not in ['stale', 'all', 'none']:
            raise ValueError("data must be one of 'stale', 'all', 'none'")
        for item in self._item_group.values():
            info = self._get_info(item)
            if (descriptors == 'all') or (descriptors == 'stale' and self._descriptor_stale(item, info)):
                heap.add_descriptor(item)
                info.descriptor_cnt = self._descriptor_cnt
            if item.value is not None:
                if (data == 'all') or (data == 'stale' and info.version != item.version):
                    heap.add_item(item)
                    info.version = item.version
        self._descriptor_cnt += 1
        return heap

    def get_heap(self, *args, **kwargs):
        """Return a new heap which contains all the new items and item
        descriptors since the last call. This is a convenience wrapper
        around :meth:`add_to_heap`.
        """
        heap = Heap(self._flavour)
        self.add_to_heap(heap, *args, **kwargs)
        return heap

    def get_end(self):
        """Return a heap that contains only an end-of-stream marker.
        """
        heap = Heap(self._flavour)
        heap.add_end()
        return heap


class ItemGroup(_spead2.ItemGroup, HeapGenerator):
    """Bundles an ItemGroup and HeapGenerator into a single class"""
    def __init__(self, *args, **kwargs):
        _spead2.ItemGroup.__init__(self)
        HeapGenerator.__init__(self, self, *args, **kwargs)
