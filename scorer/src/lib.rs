//! Telegraph WASM scorer for WEATHER_FORECAST.
//!
//! Official host ABI (wazero):
//!   rank_answer(q_ptr, q_len, gt_ptr, gt_len, ma_ptr, ma_len) -> f32
//!   alloc(size) -> i32
//!   dealloc(ptr, size)

mod scoring;

/// # Safety
/// `ptr`/`len` must refer to bytes the host just wrote via `alloc`.
#[inline]
unsafe fn read_str<'a>(ptr: i32, len: i32) -> &'a str {
    if ptr == 0 || len <= 0 {
        return "";
    }
    let slice = core::slice::from_raw_parts(ptr as *const u8, len as usize);
    core::str::from_utf8(slice).unwrap_or("")
}

#[no_mangle]
pub unsafe extern "C" fn rank_answer(
    q_ptr: i32,
    q_len: i32,
    gt_ptr: i32,
    gt_len: i32,
    ma_ptr: i32,
    ma_len: i32,
) -> f32 {
    let question = read_str(q_ptr, q_len);
    let ground_truth = read_str(gt_ptr, gt_len);
    let miner_answer = read_str(ma_ptr, ma_len);
    scoring::evaluate(question, ground_truth, miner_answer)
}

#[no_mangle]
pub unsafe extern "C" fn alloc(size: i32) -> i32 {
    if size <= 0 {
        return 0;
    }
    let mut v = Vec::<u8>::with_capacity(size as usize);
    v.set_len(size as usize);
    let ptr = v.as_mut_ptr() as i32;
    core::mem::forget(v);
    ptr
}

#[no_mangle]
pub unsafe extern "C" fn dealloc(ptr: i32, size: i32) {
    if ptr == 0 || size <= 0 {
        return;
    }
    let _ = Vec::from_raw_parts(ptr as *mut u8, size as usize, size as usize);
}

#[cfg(test)]
mod tests {
    #[test]
    fn empty_miner_is_zero() {
        assert_eq!(crate::scoring::evaluate("what is the weather", "sunny", ""), 0.0);
        assert_eq!(crate::scoring::evaluate("", "", "   "), 0.0);
    }

    #[test]
    fn self_match_beats_unrelated() {
        let q = "WEATHER_FORECAST for Berlin";
        let ans = "Berlin today: high 17C, overcast, no rain.";
        let other = "The stock market closed mixed after a volatile session.";
        let self_s = crate::scoring::evaluate(q, ans, ans);
        let cross_s = crate::scoring::evaluate(q, ans, other);
        assert!(self_s > cross_s, "self={self_s} cross={cross_s}");
        assert_eq!(self_s, 1.0);
    }
}
