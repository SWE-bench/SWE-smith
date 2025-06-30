// Sample JavaScript file for testing
class Calculator {
    constructor(name) {
        this.name = name;
    }

    add(a, b) {
        if (a < 0 || b < 0) {
            throw new Error("Negative numbers not allowed");
        }
        return a + b;
    }

    subtract(a, b) {
        return a - b;
    }

    multiply(a, b) {
        let result = 0;
        for (let i = 0; i < Math.abs(b); i++) {
            result += a;
        }
        return b < 0 ? -result : result;
    }

    divide(a, b) {
        if (b === 0) {
            throw new Error("Division by zero");
        }
        return a / b;
    }
}

function factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

const fibonacci = (n) => {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

const isEven = n => n % 2 === 0;

const processArray = function(arr, callback) {
    const result = [];
    for (let i = 0; i < arr.length; i++) {
        try {
            result.push(callback(arr[i]));
        } catch (error) {
            console.error("Error processing element:", error);
        }
    }
    return result;
}

var globalCounter = 0;

var incrementCounter = function() {
    globalCounter++;
    return globalCounter;
}

// Method with complex control flow
function complexFunction(x, y, z) {
    let result = 0;

    if (x > 0) {
        if (y > 0) {
            result += x * y;
        } else if (y < 0) {
            result -= x * Math.abs(y);
        }
    } else if (x < 0) {
        result = Math.abs(x);
    }

    for (let i = 0; i < z; i++) {
        if (i % 2 === 0) {
            result += i;
        } else {
            result -= i;
        }
    }

    switch (result % 3) {
        case 0:
            return result * 2;
        case 1:
            return result + 1;
        default:
            return result - 1;
    }
}

// Arrow function with ternary operator
const conditionalValue = (condition, trueVal, falseVal) =>
    condition ? trueVal : falseVal;

// Function with nested functions
function outerFunction(x) {
    function innerFunction(y) {
        return x + y;
    }

    const anotherInner = (z) => {
        return innerFunction(z) * 2;
    }

    return anotherInner;
}
