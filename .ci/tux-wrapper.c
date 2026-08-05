/*
 * Tux Wallpaper launcher - minimal ELF binary wrapper for AppImage
 * Runs: python3 -m tux_wallpaper
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    char *python = "/usr/bin/python3";
    char *module = "tux_wallpaper";
    char **args = malloc((argc + 3) * sizeof(char*));
    args[0] = python;
    args[1] = "-m";
    args[2] = module;
    for (int i = 1; i < argc; i++) args[i + 2] = argv[i];
    args[argc + 2] = NULL;
    execv(python, args);
    perror("execv failed");
    return 1;
}
