#include "stdio.h"
#include "windows.h"

int main(void)
{
  printf("1|2|tcp|127.0.0.1:50051|grpc\n");
  fflush(NULL);
 
  while(1)
  {
    Sleep(1);
  }
}