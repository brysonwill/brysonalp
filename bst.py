# bst.py
# Simple Binary Search Tree for rubric requirement

from dataclasses import dataclass
from typing import Optional


@dataclass
class Node:
    key: int
    left: Optional["Node"] = None
    right: Optional["Node"] = None


class BinarySearchTree:
    def __init__(self):
        self.root: Optional[Node] = None

    def insert(self, key: int) -> None:
        self.root = self._insert(self.root, key)

    def _insert(self, node: Optional[Node], key: int) -> Node:
        if node is None:
            return Node(key)

        if key < node.key:
            node.left = self._insert(node.left, key)
        elif key > node.key:
            node.right = self._insert(node.right, key)

        return node

    def find_min(self) -> Optional[int]:
        node = self.root
        if node is None:
            return None

        while node.left is not None:
            node = node.left

        return node.key

    def find_max(self) -> Optional[int]:
        node = self.root
        if node is None:
            return None

        while node.right is not None:
            node = node.right

        return node.key

    def __len__(self) -> int:
        return self._count(self.root)

    def _count(self, node: Optional[Node]) -> int:
        if node is None:
            return 0

        return 1 + self._count(node.left) + self._count(node.right)
