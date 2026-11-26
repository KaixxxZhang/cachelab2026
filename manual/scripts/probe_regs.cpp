// Live-register probe for the tile shapes used in the Part B manual.
// Build from the repo root:
//   g++ -std=c++23 -O0 -Wall -I. -o /tmp/probe_regs manual/scripts/probe_regs.cpp matrix.cpp
// The innermost line prints get_current_reg_count() while the accumulators,
// the A registers, b, k, i0, j0 and the four pointer parameters are all live.
#include "cachelab.h"
#include <iostream>
void probe_4_4(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 4; i0 = i0 + 4) {
    for (reg j0 = 0; j0 < 4; j0 = j0 + 4) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0;
      reg c30 = 0, c31 = 0, c32 = 0, c33 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg a1 = A[1];
        reg a2 = A[2];
        reg a3 = A[3];
        reg b = B[0];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b;
        b = B[1];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b;
        b = B[2];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b;
        b = B[3];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b; c33 += a3 * b;
        std::cerr << "4x4 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "4x4 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
      C[1] = c01;
      C[2] = c02;
      C[3] = c03;
      C[4] = c10;
      C[5] = c11;
      C[6] = c12;
      C[7] = c13;
      C[8] = c20;
      C[9] = c21;
      C[10] = c22;
      C[11] = c23;
      C[12] = c30;
      C[13] = c31;
      C[14] = c32;
      C[15] = c33;
    }
  }
}
void probe_4_6(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 4; i0 = i0 + 4) {
    for (reg j0 = 0; j0 < 6; j0 = j0 + 6) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0, c04 = 0, c05 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0, c14 = 0, c15 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0, c24 = 0, c25 = 0;
      reg c30 = 0, c31 = 0, c32 = 0, c33 = 0, c34 = 0, c35 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg a1 = A[1];
        reg a2 = A[2];
        reg a3 = A[3];
        reg b = B[0];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b;
        b = B[1];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b;
        b = B[2];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b;
        b = B[3];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b; c33 += a3 * b;
        b = B[4];
        c04 += a0 * b; c14 += a1 * b; c24 += a2 * b; c34 += a3 * b;
        b = B[5];
        c05 += a0 * b; c15 += a1 * b; c25 += a2 * b; c35 += a3 * b;
        std::cerr << "4x6 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "4x6 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
      C[1] = c01;
      C[2] = c02;
      C[3] = c03;
      C[4] = c04;
      C[5] = c05;
      C[6] = c10;
      C[7] = c11;
      C[8] = c12;
      C[9] = c13;
      C[10] = c14;
      C[11] = c15;
      C[12] = c20;
      C[13] = c21;
      C[14] = c22;
      C[15] = c23;
      C[16] = c24;
      C[17] = c25;
      C[18] = c30;
      C[19] = c31;
      C[20] = c32;
      C[21] = c33;
      C[22] = c34;
      C[23] = c35;
    }
  }
}
void probe_4_3(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 4; i0 = i0 + 4) {
    for (reg j0 = 0; j0 < 3; j0 = j0 + 3) {
      reg c00 = 0, c01 = 0, c02 = 0;
      reg c10 = 0, c11 = 0, c12 = 0;
      reg c20 = 0, c21 = 0, c22 = 0;
      reg c30 = 0, c31 = 0, c32 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg a1 = A[1];
        reg a2 = A[2];
        reg a3 = A[3];
        reg b = B[0];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b;
        b = B[1];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b;
        b = B[2];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b;
        std::cerr << "4x3 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "4x3 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
      C[1] = c01;
      C[2] = c02;
      C[3] = c10;
      C[4] = c11;
      C[5] = c12;
      C[6] = c20;
      C[7] = c21;
      C[8] = c22;
      C[9] = c30;
      C[10] = c31;
      C[11] = c32;
    }
  }
}
void probe_3_6(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 3; i0 = i0 + 3) {
    for (reg j0 = 0; j0 < 6; j0 = j0 + 6) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0, c04 = 0, c05 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0, c14 = 0, c15 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0, c24 = 0, c25 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg a1 = A[1];
        reg a2 = A[2];
        reg b = B[0];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b;
        b = B[1];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b;
        b = B[2];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b;
        b = B[3];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b;
        b = B[4];
        c04 += a0 * b; c14 += a1 * b; c24 += a2 * b;
        b = B[5];
        c05 += a0 * b; c15 += a1 * b; c25 += a2 * b;
        std::cerr << "3x6 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "3x6 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
      C[1] = c01;
      C[2] = c02;
      C[3] = c03;
      C[4] = c04;
      C[5] = c05;
      C[6] = c10;
      C[7] = c11;
      C[8] = c12;
      C[9] = c13;
      C[10] = c14;
      C[11] = c15;
      C[12] = c20;
      C[13] = c21;
      C[14] = c22;
      C[15] = c23;
      C[16] = c24;
      C[17] = c25;
    }
  }
}
void probe_3_3(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 3; i0 = i0 + 3) {
    for (reg j0 = 0; j0 < 3; j0 = j0 + 3) {
      reg c00 = 0, c01 = 0, c02 = 0;
      reg c10 = 0, c11 = 0, c12 = 0;
      reg c20 = 0, c21 = 0, c22 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg a1 = A[1];
        reg a2 = A[2];
        reg b = B[0];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b;
        b = B[1];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b;
        b = B[2];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b;
        std::cerr << "3x3 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "3x3 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
      C[1] = c01;
      C[2] = c02;
      C[3] = c10;
      C[4] = c11;
      C[5] = c12;
      C[6] = c20;
      C[7] = c21;
      C[8] = c22;
    }
  }
}
void probe_2_8(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 2; i0 = i0 + 2) {
    for (reg j0 = 0; j0 < 8; j0 = j0 + 8) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0, c04 = 0, c05 = 0, c06 = 0, c07 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0, c14 = 0, c15 = 0, c16 = 0, c17 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg a1 = A[1];
        reg b = B[0];
        c00 += a0 * b; c10 += a1 * b;
        b = B[1];
        c01 += a0 * b; c11 += a1 * b;
        b = B[2];
        c02 += a0 * b; c12 += a1 * b;
        b = B[3];
        c03 += a0 * b; c13 += a1 * b;
        b = B[4];
        c04 += a0 * b; c14 += a1 * b;
        b = B[5];
        c05 += a0 * b; c15 += a1 * b;
        b = B[6];
        c06 += a0 * b; c16 += a1 * b;
        b = B[7];
        c07 += a0 * b; c17 += a1 * b;
        std::cerr << "2x8 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "2x8 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
      C[1] = c01;
      C[2] = c02;
      C[3] = c03;
      C[4] = c04;
      C[5] = c05;
      C[6] = c06;
      C[7] = c07;
      C[8] = c10;
      C[9] = c11;
      C[10] = c12;
      C[11] = c13;
      C[12] = c14;
      C[13] = c15;
      C[14] = c16;
      C[15] = c17;
    }
  }
}
void probe_5_4(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 5; i0 = i0 + 5) {
    for (reg j0 = 0; j0 < 4; j0 = j0 + 4) {
      reg c00 = 0, c01 = 0, c02 = 0, c03 = 0;
      reg c10 = 0, c11 = 0, c12 = 0, c13 = 0;
      reg c20 = 0, c21 = 0, c22 = 0, c23 = 0;
      reg c30 = 0, c31 = 0, c32 = 0, c33 = 0;
      reg c40 = 0, c41 = 0, c42 = 0, c43 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg a1 = A[1];
        reg a2 = A[2];
        reg a3 = A[3];
        reg a4 = A[4];
        reg b = B[0];
        c00 += a0 * b; c10 += a1 * b; c20 += a2 * b; c30 += a3 * b; c40 += a4 * b;
        b = B[1];
        c01 += a0 * b; c11 += a1 * b; c21 += a2 * b; c31 += a3 * b; c41 += a4 * b;
        b = B[2];
        c02 += a0 * b; c12 += a1 * b; c22 += a2 * b; c32 += a3 * b; c42 += a4 * b;
        b = B[3];
        c03 += a0 * b; c13 += a1 * b; c23 += a2 * b; c33 += a3 * b; c43 += a4 * b;
        std::cerr << "5x4 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "5x4 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
      C[1] = c01;
      C[2] = c02;
      C[3] = c03;
      C[4] = c10;
      C[5] = c11;
      C[6] = c12;
      C[7] = c13;
      C[8] = c20;
      C[9] = c21;
      C[10] = c22;
      C[11] = c23;
      C[12] = c30;
      C[13] = c31;
      C[14] = c32;
      C[15] = c33;
      C[16] = c40;
      C[17] = c41;
      C[18] = c42;
      C[19] = c43;
    }
  }
}
void probe_1_1(ptr_reg A, ptr_reg B, ptr_reg C, ptr_reg buffer) {
  (void)buffer;
  for (reg i0 = 0; i0 < 1; i0 = i0 + 1) {
    for (reg j0 = 0; j0 < 1; j0 = j0 + 1) {
      reg c00 = 0;
      for (reg k = 0; k < 1; k = k + 1) {
        reg a0 = A[0];
        reg b = B[0];
        c00 += a0 * b;
        std::cerr << "1x1 inner " << get_current_reg_count() << "\n";
      }
      std::cerr << "1x1 after-k " << get_current_reg_count() << "\n";
      C[0] = c00;
    }
  }
}
template <typename F>
void run(F fn, const char* name) {
  max_reg_count = 0;
  auto tup = init(8, 8, 8);
  ptr_reg A = std::move(std::get<0>(tup));
  ptr_reg B = std::move(std::get<1>(tup));
  ptr_reg C = std::move(std::get<2>(tup));
  ptr_reg buffer = std::move(std::get<3>(tup));
  fn(std::move(A), std::move(B), std::move(C), std::move(buffer));
  std::cerr << name << " max " << get_max_reg_count() << "\n";
}
int main() {
  run(probe_4_4, "4x4");
  run(probe_4_6, "4x6");
  run(probe_4_3, "4x3");
  run(probe_3_6, "3x6");
  run(probe_3_3, "3x3");
  run(probe_2_8, "2x8");
  run(probe_5_4, "5x4");
  run(probe_1_1, "1x1");
}
