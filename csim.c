// student id: 2025200673
// please change the above line to your student id
#define _POSIX_C_SOURCE 200809L
#include <getopt.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

void printSummary(int hits, int misses, int evictions)
{
  printf("hits:%d misses:%d evictions:%d\n", hits, misses, evictions);
  FILE *output_fp = fopen(".csim_results", "w");
  assert(output_fp);
  fprintf(output_fp, "%d %d %d\n", hits, misses, evictions);
  fclose(output_fp);
}

void printHelp(const char *name)
{
  printf(
      "Usage: %s [-hv] -s <num> -E <num> -b <num> -t <file>\n"
      "Options:\n"
      "  -h         Print this help message.\n"
      "  -v         Optional verbose flag.\n"
      "  -s <num>   Number of set index bits.\n"
      "  -E <num>   Number of lines per set.\n"
      "  -b <num>   Number of block offset bits.\n"
      "  -t <file>  Trace file.\n\n"
      "Examples:\n"
      "  linux>  %s -s 4 -E 1 -b 4 -t traces/yi.trace\n"
      "  linux>  %s -v -s 8 -E 2 -b 4 -t traces/yi.trace\n",
      name, name, name);
}

typedef struct{
  int valid;
  unsigned long tag;
  int stamp;
}CacheLine;

int main(int argc, char *argv[])
{
  int s = -1;
  int E = -1;
  int b = -1;
  int verbose = 0;
  char* tracefile = NULL;
  int opt;

  while((opt = getopt(argc, argv, "hvs:E:b:t:")) != -1){
    switch(opt){
      case 'h':
        printHelp(argv[0]);
        return 0;
      case 'v':
        verbose = 1;
        break;
      case 's':
        s = atoi(optarg);
        break;
      case 'E':
        E = atoi(optarg);
        break;
      case 'b':
        b = atoi(optarg);
        break;
      case 't':
        tracefile = optarg;
        break;
      default:
        printHelp(argv[0]);
        return 1;
    }
  }

  if(s<0||E<=0||b<0||tracefile == NULL){
    printHelp(argv[0]);
    return 1;
  }

  int set_count = 1 << s;
  CacheLine *cache = calloc((size_t)set_count * (size_t)E, sizeof(CacheLine));
  if(cache == NULL){
    fprintf(stderr, "cannot allocate cache\n");
    return 1;
  }

  FILE *fp = fopen(tracefile, "r");
  if(fp == NULL){
    fprintf(stderr, "cannot open %s\n", tracefile);
    free(cache);
    return 1;
  }

  int hits = 0;
  int misses = 0;
  int evictions = 0;
  int stamp = 0;

  char op;
  unsigned long addr;
  int size;
  int regid;

  while(fscanf(fp, " %c %lx,%d %d", &op, &addr, &size, &regid)==4){
    if(op != 'L' && op !='S'){
      continue;
    }
    if(verbose){
      fprintf(stderr, "%c %lx,%d %d\n", op, addr, size, regid);
    }

    unsigned long block = addr >> b;
    int set_index = (int)(block & ((1UL << s) - 1));
    unsigned long tag = block >> s;
    CacheLine *lines = cache + (size_t)set_index * (size_t)E;

    int hit_at = -1;
    int empty_at = -1;
    int lru_at = 0;
    for(int i=0; i<E; i++){
      if(lines[i].valid && lines[i].tag == tag){
        hit_at = i;
      }
      if(!lines[i].valid && empty_at < 0){
        empty_at = i;
      }
      if(lines[i].valid && lines[i].stamp < lines[lru_at].stamp){
        lru_at = i;
      }
    }

    stamp++;
    if(hit_at >= 0){
      hits++;
      lines[hit_at].stamp = stamp;
    }
    else{
      misses++;
      int dest;
      if(empty_at >= 0){
        dest = empty_at;
      }
      else{
        evictions++;
        dest = lru_at;
      }
      lines[dest].valid = 1;
      lines[dest].tag = tag;
      lines[dest].stamp = stamp;
    }
  }
  fclose(fp);
  free(cache);
  // printHelp(argv[0]);
  printSummary(hits, misses, evictions);
  return 0;
}
