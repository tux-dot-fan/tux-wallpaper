#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    char *python_path = PYTHON_PATH;
    char *script_path = SCRIPT_PATH;
    execv(python_path, (char*[]){ python_path, script_path, NULL });
    perror("execv failed");
    return 1;
}
