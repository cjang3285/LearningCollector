# React Hooks Best Practices

#### You:
What are some common mistakes when using useEffect in React?

#### ChatGPT:
Great question! Here are the most common mistakes developers make with `useEffect`:

## 1. Missing Dependencies

```javascript
// ❌ Bad - missing count dependency
useEffect(() => {
  console.log(count);
}, []); // count is not in dependency array

// ✅ Good
useEffect(() => {
  console.log(count);
}, [count]);
```

## 2. Unnecessary Re-renders

```javascript
// ❌ Bad - object created every render
useEffect(() => {
  fetchData(options);
}, [options]); // options is a new object every render

// ✅ Good - use useMemo
const options = useMemo(() => ({ limit: 10 }), []);
useEffect(() => {
  fetchData(options);
}, [options]);
```

## 3. Not Cleaning Up

```javascript
// ❌ Bad - no cleanup
useEffect(() => {
  const interval = setInterval(() => tick(), 1000);
}, []);

// ✅ Good - cleanup function
useEffect(() => {
  const interval = setInterval(() => tick(), 1000);
  return () => clearInterval(interval);
}, []);
```

## 4. Fetching Data Without Handling Race Conditions

```javascript
// ❌ Bad - race condition
useEffect(() => {
  fetchUser(userId).then(user => setUser(user));
}, [userId]);

// ✅ Good - ignore stale responses
useEffect(() => {
  let ignore = false;
  fetchUser(userId).then(user => {
    if (!ignore) setUser(user);
  });
  return () => { ignore = true; };
}, [userId]);
```

#### You:
Should I use useEffect or useLayoutEffect for DOM measurements?

#### ChatGPT:
Use `useLayoutEffect` for DOM measurements! Here's why:

**useLayoutEffect** fires **synchronously** after DOM mutations but **before** the browser paints. This prevents visual flickering.

**useEffect** fires **asynchronously after** the browser paints, which can cause visible layout shifts.

Example:

```javascript
// ✅ Good - useLayoutEffect for measurements
function Tooltip() {
  const [height, setHeight] = useState(0);
  const ref = useRef(null);

  useLayoutEffect(() => {
    const measured = ref.current.getBoundingClientRect().height;
    setHeight(measured);
  }, []);

  return <div ref={ref}>Tooltip content</div>;
}
```

**Rule of thumb:**
- DOM measurements/mutations → `useLayoutEffect`
- Data fetching/subscriptions → `useEffect`
