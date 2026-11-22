/*
请注意，你的代码不能出现任何 int/short/char/float/double/auto 等局部变量/函数传参，我们仅允许使用 reg 定义的寄存器变量。
其中 reg 等价于一个 int。

你不能自己申请额外的内存，即不能使用 new/malloc，作为补偿我们传入了一段 buffer，大小为 BUFFER_SIZE = 64，你可以视情况使用。

我们的数组按照 A, B, C, buffer 的顺序在内存上连续紧密排列，且 &A = 0x30000000（这是模拟的设定，不是 A 的真实地址）

如果你需要以更自由的方式访问内存，你可以以相对 A 的方式访问，比如 A[100]，用 *(0x30000000) 是无法访问到的。

如果你有定义常量的需求（更严谨的说法是，你想定义的是汇编层面的立即数，不应该占用寄存器），请参考下面这种方式使用宏定义来完成。
*/

#include "cachelab.h"

#define m case0_m
#define n case0_n
#define p case0_p

// 我们用这个 2*2*2 的矩阵乘法来演示寄存器是怎么被分配的
void gemm_case0(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer)
{ // allocate 0 1 2 3
  for (reg i = 0; i < m; ++i)
  { // allocate 4
    for (reg j = 0; j < p; ++j)
    {               // allocate 5
      reg tmpc = 0; // allocate 6
      for (reg k = 0; k < n; ++k)
      {                          // allocate 7
        reg tmpa = A[i * n + k]; // allocate 8
        reg tmpb = B[k * p + j]; // allocate 9
        tmpc += tmpa * tmpb;
      } // free 9 8
      // free 7
      C[i * p + j] = tmpc;
    } // free 6
    // free 5
  }
  // free 4
} // free 3 2 1 0

#undef m
#undef n
#undef p

#define m case1_m
#define n case1_n
#define p case1_p

void gemm_case1(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer)
{
  (void)buffer;
  for (reg i0 = 0; i0 < m; i0 = i0 + 4) {
    for (reg j0 = 0; j0 < p; j0 = j0 + 4) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0;
      reg c30 = 0, c31 = 0, c32 = 0, c33 = 0;
      for (reg k = 0; k < n; k = k + 1) {
        reg a0 = A[(i0 + 0) * n + k];
        reg a1 = A[(i0 + 1) * n + k];
        reg a2 = A[(i0 + 2) * n + k];
        reg a3 = A[(i0 + 3) * n + k];
        reg b = B[k * p + (j0 + 0)];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b;
        b = B[k * p + (j0 + 1)];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b;
        b = B[k * p + (j0 + 2)];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b;
        b = B[k * p + (j0 + 3)];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b; c33 += a3 * b;
      }
      C[(i0 + 0) * p + (j0 + 0)] = c00;
      C[(i0 + 0) * p + (j0 + 1)] = c01;
      C[(i0 + 0) * p + (j0 + 2)] = c02;
      C[(i0 + 0) * p + (j0 + 3)] = c03;
      C[(i0 + 1) * p + (j0 + 0)] = c10;
      C[(i0 + 1) * p + (j0 + 1)] = c11;
      C[(i0 + 1) * p + (j0 + 2)] = c12;
      C[(i0 + 1) * p + (j0 + 3)] = c13;
      C[(i0 + 2) * p + (j0 + 0)] = c20;
      C[(i0 + 2) * p + (j0 + 1)] = c21;
      C[(i0 + 2) * p + (j0 + 2)] = c22;
      C[(i0 + 2) * p + (j0 + 3)] = c23;
      C[(i0 + 3) * p + (j0 + 0)] = c30;
      C[(i0 + 3) * p + (j0 + 1)] = c31;
      C[(i0 + 3) * p + (j0 + 2)] = c32;
      C[(i0 + 3) * p + (j0 + 3)] = c33;
    }
  }
}

#undef m
#undef n
#undef p

#define m case2_m
#define n case2_n
#define p case2_p

void gemm_case2(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer)
{
  (void)buffer;
  for (reg i0 = 0; i0 < m; i0 = i0 + 4) {
    for (reg j0 = 0; j0 < p; j0 = j0 + 4) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0;
      reg c30 = 0, c31 = 0, c32 = 0, c33 = 0;
      for (reg k = 0; k < n; k = k + 1) {
        reg a0 = A[(i0 + 0) * n + k];
        reg a1 = A[(i0 + 1) * n + k];
        reg a2 = A[(i0 + 2) * n + k];
        reg a3 = A[(i0 + 3) * n + k];
        reg b = B[k * p + (j0 + 0)];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b;
        b = B[k * p + (j0 + 1)];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b;
        b = B[k * p + (j0 + 2)];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b;
        b = B[k * p + (j0 + 3)];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b; c33 += a3 * b;
      }
      C[(i0 + 0) * p + (j0 + 0)] = c00;
      C[(i0 + 0) * p + (j0 + 1)] = c01;
      C[(i0 + 0) * p + (j0 + 2)] = c02;
      C[(i0 + 0) * p + (j0 + 3)] = c03;
      C[(i0 + 1) * p + (j0 + 0)] = c10;
      C[(i0 + 1) * p + (j0 + 1)] = c11;
      C[(i0 + 1) * p + (j0 + 2)] = c12;
      C[(i0 + 1) * p + (j0 + 3)] = c13;
      C[(i0 + 2) * p + (j0 + 0)] = c20;
      C[(i0 + 2) * p + (j0 + 1)] = c21;
      C[(i0 + 2) * p + (j0 + 2)] = c22;
      C[(i0 + 2) * p + (j0 + 3)] = c23;
      C[(i0 + 3) * p + (j0 + 0)] = c30;
      C[(i0 + 3) * p + (j0 + 1)] = c31;
      C[(i0 + 3) * p + (j0 + 2)] = c32;
      C[(i0 + 3) * p + (j0 + 3)] = c33;
    }
  }
}

#undef m
#undef n
#undef p

#define m case3_m
#define n case3_n
#define p case3_p

void gemm_case3(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer)
{
  (void)buffer;
  for (reg i0 = 0; i0 + 3 < m; i0 = i0 + 4) {
    for (reg j0 = 0; j0 + 5 < p; j0 = j0 + 6) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0, c04 = 0, c05 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0, c14 = 0, c15 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0, c24 = 0, c25 = 0;
      reg c30 = 0, c31 = 0, c32 = 0, c33 = 0, c34 = 0, c35 = 0;
      for (reg k = 0; k < n; k = k + 1) {
        reg a0 = A[(i0 + 0) * n + k];
        reg a1 = A[(i0 + 1) * n + k];
        reg a2 = A[(i0 + 2) * n + k];
        reg a3 = A[(i0 + 3) * n + k];
        reg b = B[k * p + (j0 + 0)];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b;
        b = B[k * p + (j0 + 1)];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b;
        b = B[k * p + (j0 + 2)];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b;
        b = B[k * p + (j0 + 3)];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b; c33 += a3 * b;
        b = B[k * p + (j0 + 4)];
        c04 += a0 * b; c14 += a1 * b; c24 += a2 * b; c34 += a3 * b;
        b = B[k * p + (j0 + 5)];
        c05 += a0 * b; c15 += a1 * b; c25 += a2 * b; c35 += a3 * b;
      }
      C[(i0 + 0) * p + (j0 + 0)] = c00;
      C[(i0 + 0) * p + (j0 + 1)] = c01;
      C[(i0 + 0) * p + (j0 + 2)] = c02;
      C[(i0 + 0) * p + (j0 + 3)] = c03;
      C[(i0 + 0) * p + (j0 + 4)] = c04;
      C[(i0 + 0) * p + (j0 + 5)] = c05;
      C[(i0 + 1) * p + (j0 + 0)] = c10;
      C[(i0 + 1) * p + (j0 + 1)] = c11;
      C[(i0 + 1) * p + (j0 + 2)] = c12;
      C[(i0 + 1) * p + (j0 + 3)] = c13;
      C[(i0 + 1) * p + (j0 + 4)] = c14;
      C[(i0 + 1) * p + (j0 + 5)] = c15;
      C[(i0 + 2) * p + (j0 + 0)] = c20;
      C[(i0 + 2) * p + (j0 + 1)] = c21;
      C[(i0 + 2) * p + (j0 + 2)] = c22;
      C[(i0 + 2) * p + (j0 + 3)] = c23;
      C[(i0 + 2) * p + (j0 + 4)] = c24;
      C[(i0 + 2) * p + (j0 + 5)] = c25;
      C[(i0 + 3) * p + (j0 + 0)] = c30;
      C[(i0 + 3) * p + (j0 + 1)] = c31;
      C[(i0 + 3) * p + (j0 + 2)] = c32;
      C[(i0 + 3) * p + (j0 + 3)] = c33;
      C[(i0 + 3) * p + (j0 + 4)] = c34;
      C[(i0 + 3) * p + (j0 + 5)] = c35;
    }
    for (reg j0 = p - 3; j0 + 2 < p; j0 = j0 + 3) {
      reg c00 = 0, c01 = 0, c02 = 0;
      reg c10 = 0, c11 = 0, c12 = 0;
      reg c20 = 0, c21 = 0, c22 = 0;
      reg c30 = 0, c31 = 0, c32 = 0;
      for (reg k = 0; k < n; k = k + 1) {
        reg a0 = A[(i0 + 0) * n + k];
        reg a1 = A[(i0 + 1) * n + k];
        reg a2 = A[(i0 + 2) * n + k];
        reg a3 = A[(i0 + 3) * n + k];
        reg b = B[k * p + (j0 + 0)];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b;
        b = B[k * p + (j0 + 1)];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b;
        b = B[k * p + (j0 + 2)];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b;
      }
      C[(i0 + 0) * p + (j0 + 0)] = c00;
      C[(i0 + 0) * p + (j0 + 1)] = c01;
      C[(i0 + 0) * p + (j0 + 2)] = c02;
      C[(i0 + 1) * p + (j0 + 0)] = c10;
      C[(i0 + 1) * p + (j0 + 1)] = c11;
      C[(i0 + 1) * p + (j0 + 2)] = c12;
      C[(i0 + 2) * p + (j0 + 0)] = c20;
      C[(i0 + 2) * p + (j0 + 1)] = c21;
      C[(i0 + 2) * p + (j0 + 2)] = c22;
      C[(i0 + 3) * p + (j0 + 0)] = c30;
      C[(i0 + 3) * p + (j0 + 1)] = c31;
      C[(i0 + 3) * p + (j0 + 2)] = c32;
    }
  }
  for (reg i0 = m - 3; i0 + 2 < m; i0 = i0 + 3) {
    for (reg j0 = 0; j0 + 5 < p; j0 = j0 + 6) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0, c04 = 0, c05 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0, c14 = 0, c15 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0, c24 = 0, c25 = 0;
      for (reg k = 0; k < n; k = k + 1) {
        reg a0 = A[(i0 + 0) * n + k];
        reg a1 = A[(i0 + 1) * n + k];
        reg a2 = A[(i0 + 2) * n + k];
        reg b = B[k * p + (j0 + 0)];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b;
        b = B[k * p + (j0 + 1)];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b;
        b = B[k * p + (j0 + 2)];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b;
        b = B[k * p + (j0 + 3)];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b;
        b = B[k * p + (j0 + 4)];
        c04 += a0 * b; c14 += a1 * b; c24 += a2 * b;
        b = B[k * p + (j0 + 5)];
        c05 += a0 * b; c15 += a1 * b; c25 += a2 * b;
      }
      C[(i0 + 0) * p + (j0 + 0)] = c00;
      C[(i0 + 0) * p + (j0 + 1)] = c01;
      C[(i0 + 0) * p + (j0 + 2)] = c02;
      C[(i0 + 0) * p + (j0 + 3)] = c03;
      C[(i0 + 0) * p + (j0 + 4)] = c04;
      C[(i0 + 0) * p + (j0 + 5)] = c05;
      C[(i0 + 1) * p + (j0 + 0)] = c10;
      C[(i0 + 1) * p + (j0 + 1)] = c11;
      C[(i0 + 1) * p + (j0 + 2)] = c12;
      C[(i0 + 1) * p + (j0 + 3)] = c13;
      C[(i0 + 1) * p + (j0 + 4)] = c14;
      C[(i0 + 1) * p + (j0 + 5)] = c15;
      C[(i0 + 2) * p + (j0 + 0)] = c20;
      C[(i0 + 2) * p + (j0 + 1)] = c21;
      C[(i0 + 2) * p + (j0 + 2)] = c22;
      C[(i0 + 2) * p + (j0 + 3)] = c23;
      C[(i0 + 2) * p + (j0 + 4)] = c24;
      C[(i0 + 2) * p + (j0 + 5)] = c25;
    }
    for (reg j0 = p - 3; j0 + 2 < p; j0 = j0 + 3) {
      reg c00 = 0, c01 = 0, c02 = 0;
      reg c10 = 0, c11 = 0, c12 = 0;
      reg c20 = 0, c21 = 0, c22 = 0;
      for (reg k = 0; k < n; k = k + 1) {
        reg a0 = A[(i0 + 0) * n + k];
        reg a1 = A[(i0 + 1) * n + k];
        reg a2 = A[(i0 + 2) * n + k];
        reg b = B[k * p + (j0 + 0)];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b;
        b = B[k * p + (j0 + 1)];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b;
        b = B[k * p + (j0 + 2)];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b;
      }
      C[(i0 + 0) * p + (j0 + 0)] = c00;
      C[(i0 + 0) * p + (j0 + 1)] = c01;
      C[(i0 + 0) * p + (j0 + 2)] = c02;
      C[(i0 + 1) * p + (j0 + 0)] = c10;
      C[(i0 + 1) * p + (j0 + 1)] = c11;
      C[(i0 + 1) * p + (j0 + 2)] = c12;
      C[(i0 + 2) * p + (j0 + 0)] = c20;
      C[(i0 + 2) * p + (j0 + 1)] = c21;
      C[(i0 + 2) * p + (j0 + 2)] = c22;
    }
  }
}

#undef m
#undef n
#undef p