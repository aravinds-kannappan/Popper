// The live evaluation set. Each item is a claim with a known ground truth. Some
// are true, some are false, and several of the false ones are the kind of thing a
// language model states confidently and gets wrong, which is the point: that is
// where running AXLE actually changes the answer.
//
// truth = "TRUE"  the claim holds
// truth = "FALSE" the claim is false; `counterexample` is one witness

export type EvalItem = {
  id: string;
  question: string;       // asked to both systems, in natural language
  truth: "TRUE" | "FALSE";
  counterexample?: string; // a reference witness, shown to the evaluator only
  note?: string;           // why it is interesting
};

export const EVAL_SET: EvalItem[] = [
  {
    id: "nat_lt_5",
    question: "Is it true that every natural number n satisfies n < 5?",
    truth: "FALSE",
    counterexample: "n = 5 (5 < 5 is false)",
    note: "easy: a plain check should get this",
  },
  {
    id: "nat_sub_add",
    question:
      "Using natural-number (truncated) subtraction, does (a - b) + b = a hold for all naturals a and b?",
    truth: "FALSE",
    counterexample: "a = 0, b = 1: (0 - 1) + 1 = 0 + 1 = 1, not 0",
    note: "subtle: models often say true, forgetting truncated subtraction",
  },
  {
    id: "euler_prime",
    question: "Is n^2 - n + 41 prime for every natural number n?",
    truth: "FALSE",
    counterexample: "n = 41: 41^2 - 41 + 41 = 41^2 = 1681 = 41 x 41, not prime",
    note: "classic trap: true for small n, fails at n = 41",
  },
  {
    id: "two_pow_gt_nsq",
    question: "Is 2^n > n^2 for every natural number n with n >= 1?",
    truth: "FALSE",
    counterexample: "n = 3: 2^3 = 8, but 3^2 = 9, so 8 > 9 is false",
    note: "subtle: holds for n=1 then fails at n=2,3,4 before holding again",
  },
  {
    id: "sum_odds",
    question: "Is the sum of the first n odd numbers equal to n^2 for every n?",
    truth: "TRUE",
    note: "true: a faithful checker should not raise a false alarm",
  },
  {
    id: "sq_ge_self_int",
    question: "For every integer n, is n^2 >= n?",
    truth: "TRUE",
    note: "true over the integers; a checker must not wrongly flag it",
  },
];
