use crate::objects::{Key, Value};
use std::fmt::Debug;

/// A trait for map-like values that can provide CEL-compatible key lookup and
/// iteration semantics.
pub trait MapValue: Debug + Send + Sync {
    /// Returns the value for the given key if present.
    fn get(&self, key: &Key) -> Option<Value>;

    /// Returns true if the key exists in the map.
    fn contains_key(&self, key: &Key) -> bool;

    /// Returns the number of entries in the map.
    fn len(&self) -> usize;

    /// Returns an iterator over key/value pairs. Implementations may clone the
    /// underlying data as needed.
    fn iter(&self) -> Box<dyn Iterator<Item = (Key, Value)> + '_>;
}
